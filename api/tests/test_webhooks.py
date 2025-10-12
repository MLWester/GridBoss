from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import (
    BillingAccount,
    League,
    LeagueRole,
    Membership,
    StripeEvent,
    Subscription,
    User,
)
from app.db.session import get_session
from app.main import app
from app.services.plan import GRACE_PERIOD_DAYS

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

for table in Base.metadata.sorted_tables:
    for column in table.c:
        default = getattr(column, "server_default", None)
        if (
            default is not None
            and hasattr(default, "arg")
            and "gen_random_uuid" in str(default.arg)
        ):
            column.server_default = None

Base.metadata.create_all(bind=engine)


def reset_database() -> None:
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_database()
    get_settings.cache_clear()
    settings = Settings(
        APP_ENV="test",
        APP_URL="http://localhost:5173",
        API_URL="http://localhost:8000",
        DISCORD_CLIENT_ID="client",
        DISCORD_CLIENT_SECRET="secret",
        DISCORD_REDIRECT_URI="http://localhost:8000/auth/discord/callback",
        JWT_SECRET="secret",
        JWT_ACCESS_TTL_MIN=15,
        JWT_REFRESH_TTL_DAYS=14,
        CORS_ORIGINS="http://localhost:5173",
        REDIS_URL="redis://localhost:6379/0",
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PRICE_PRO="price_pro",
        STRIPE_PRICE_ELITE="price_elite",
        STRIPE_WEBHOOK_SECRET="test-secret",
    )

    def get_test_session() -> Session:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = get_test_session

    yield

    app.dependency_overrides.clear()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def sync_spy(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    import worker.jobs.stripe as stripe_jobs

    calls: list[str] = []
    monkeypatch.setattr(
        stripe_jobs.sync_plan_from_stripe, "send", lambda customer_id: calls.append(customer_id)
    )
    return calls


def create_user(session: Session) -> User:
    user = User(
        discord_id=str(uuid4()), discord_username="user", email=f"{uuid4().hex}@example.com"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_owner(session: Session) -> tuple[User, League]:
    owner = create_user(session)
    league = League(name="League", slug=f"league-{uuid4().hex[:8]}", owner_id=owner.id)
    session.add(league)
    session.commit()
    session.refresh(league)
    membership = Membership(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER)
    session.add(membership)
    session.commit()
    return owner, league


def make_headers() -> dict[str, str]:
    return {
        "Stripe-Signature": "test-secret",
        "Content-Type": "application/json",
    }


def test_missing_signature(client: TestClient) -> None:
    response = client.post("/webhooks/stripe", content="{}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MISSING_SIGNATURE"


def test_invalid_signature(client: TestClient) -> None:
    response = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "invalid"},
        content="{}",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SIGNATURE"


def test_checkout_completed_creates_subscription(client: TestClient) -> None:
    session = TestingSessionLocal()
    owner, _ = create_owner(session)
    billing = BillingAccount(owner_user_id=owner.id, plan="FREE", stripe_customer_id="cus_123")
    session.add(billing)
    session.commit()

    event = {
        "id": "evt_checkout",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_123",
                "subscription": "sub_123",
                "metadata": {"plan": "PRO"},
            }
        },
    }

    response = client.post(
        "/webhooks/stripe",
        headers=make_headers(),
        content=json.dumps(event),
    )

    assert response.status_code == 200
    session.close()
    verify = TestingSessionLocal()
    stripe_event = verify.execute(
        select(StripeEvent).where(StripeEvent.event_id == "evt_checkout")
    ).scalar_one()
    assert stripe_event is not None
    subscription = verify.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_123")
    ).scalar_one()
    assert subscription.plan == "PRO"
    billing = verify.execute(
        select(BillingAccount).where(BillingAccount.owner_user_id == owner.id)
    ).scalar_one()
    assert billing.plan == "PRO"
    league = verify.execute(select(League).where(League.owner_id == owner.id)).scalar_one()
    assert league.plan == "PRO"
    verify.close()


def test_subscription_updated_updates_plan_and_enqueues_sync(
    client: TestClient, sync_spy: list[str]
) -> None:
    session = TestingSessionLocal()
    owner, _ = create_owner(session)
    billing = BillingAccount(owner_user_id=owner.id, plan="PRO", stripe_customer_id="cus_456")
    session.add(billing)
    session.commit()
    session.refresh(billing)
    subscription = Subscription(
        billing_account_id=billing.id,
        stripe_subscription_id="sub_456",
        plan="PRO",
        status="active",
    )
    session.add(subscription)
    session.commit()

    current_period_end = int(datetime.now(tz=UTC).timestamp())
    event = {
        "id": "evt_update",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_456",
                "customer": "cus_456",
                "status": "active",
                "current_period_end": current_period_end,
                "items": {
                    "data": [
                        {
                            "price": {"id": "price_elite"},
                        }
                    ]
                },
            }
        },
    }

    response = client.post(
        "/webhooks/stripe",
        headers=make_headers(),
        content=json.dumps(event),
    )

    assert response.status_code == 200
    session.close()
    verify = TestingSessionLocal()
    subscription = verify.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_456")
    ).scalar_one()
    assert subscription.plan == "ELITE"
    assert subscription.status == "active"
    billing = verify.execute(
        select(BillingAccount).where(BillingAccount.owner_user_id == owner.id)
    ).scalar_one()
    assert billing.plan == "ELITE"
    assert billing.plan_grace_plan is None
    assert billing.plan_grace_expires_at is None
    league = verify.execute(select(League).where(League.owner_id == owner.id)).scalar_one()
    assert league.driver_limit == 9999
    stored_end = billing.current_period_end
    assert stored_end is not None
    if stored_end.tzinfo is None:
        stored_end = stored_end.replace(tzinfo=UTC)
    assert int(stored_end.timestamp()) == current_period_end
    assert sync_spy == ["cus_456"]
    verify.close()


def test_subscription_deleted_sets_free(client: TestClient) -> None:
    session = TestingSessionLocal()
    owner, _ = create_owner(session)
    billing = BillingAccount(owner_user_id=owner.id, plan="PRO", stripe_customer_id="cus_789")
    session.add(billing)
    session.commit()
    session.refresh(billing)
    subscription = Subscription(
        billing_account_id=billing.id,
        stripe_subscription_id="sub_789",
        plan="PRO",
        status="active",
    )
    session.add(subscription)
    session.commit()

    event = {
        "id": "evt_deleted",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_789", "customer": "cus_789"}},
    }

    response = client.post(
        "/webhooks/stripe",
        headers=make_headers(),
        content=json.dumps(event),
    )

    assert response.status_code == 200
    session.close()
    verify = TestingSessionLocal()
    subscription = verify.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_789")
    ).scalar_one()
    assert subscription.status == "canceled"
    billing = verify.execute(
        select(BillingAccount).where(BillingAccount.owner_user_id == owner.id)
    ).scalar_one()
    assert billing.plan == "FREE"
    assert billing.plan_grace_plan == "PRO"
    assert billing.plan_grace_expires_at is not None
    grace_expires = billing.plan_grace_expires_at
    if grace_expires.tzinfo is None:
        grace_expires = grace_expires.replace(tzinfo=UTC)
    remaining = grace_expires - datetime.now(UTC)
    assert remaining.total_seconds() > 0
    assert remaining <= timedelta(days=GRACE_PERIOD_DAYS, seconds=5)
    league = verify.execute(select(League).where(League.owner_id == owner.id)).scalar_one()
    assert league.driver_limit == 20
    verify.close()


def test_invoice_payment_failed_marks_past_due(client: TestClient) -> None:
    session = TestingSessionLocal()
    owner, _ = create_owner(session)
    billing = BillingAccount(owner_user_id=owner.id, plan="PRO", stripe_customer_id="cus_inv")
    session.add(billing)
    session.commit()
    session.refresh(billing)
    subscription = Subscription(
        billing_account_id=billing.id,
        stripe_subscription_id="sub_inv",
        plan="PRO",
        status="active",
    )
    session.add(subscription)
    session.commit()

    event = {
        "id": "evt_invoice",
        "type": "invoice.payment_failed",
        "data": {"object": {"subscription": "sub_inv", "customer": "cus_inv"}},
    }

    response = client.post(
        "/webhooks/stripe",
        headers=make_headers(),
        content=json.dumps(event),
    )

    assert response.status_code == 200
    session.close()
    verify = TestingSessionLocal()
    subscription = verify.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_inv")
    ).scalar_one()
    assert subscription.status == "past_due"
    verify.close()


def test_idempotent_event_ignored(client: TestClient) -> None:
    session = TestingSessionLocal()
    owner, _ = create_owner(session)
    billing = BillingAccount(owner_user_id=owner.id, plan="PRO", stripe_customer_id="cus_dupe")
    session.add(billing)
    session.commit()

    event = {
        "id": "evt_dupe",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_dupe",
                "subscription": "sub_dupe",
                "metadata": {"plan": "PRO"},
            }
        },
    }

    payload = json.dumps(event)
    headers = make_headers()

    first = client.post("/webhooks/stripe", headers=headers, content=payload)
    second = client.post("/webhooks/stripe", headers=headers, content=payload)

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.status_code == 200
    assert second.json()["status"] == "ignored"
    events = (
        session.execute(select(StripeEvent).where(StripeEvent.event_id == "evt_dupe"))
        .scalars()
        .all()
    )
    assert len(events) == 1
    session.close()
