from __future__ import annotations

import sys
import types

if "stripe" not in sys.modules:
    stripe_module = types.ModuleType("stripe")
    stripe_module.Customer = types.SimpleNamespace(create=lambda **kwargs: {"id": "stub_customer"})
    stripe_module.checkout = types.SimpleNamespace(
        Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_checkout"})
    )
    stripe_module.billing_portal = types.SimpleNamespace(
        Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_portal"})
    )
    stripe_module.error = types.SimpleNamespace(StripeError=Exception)
    sys.modules["stripe"] = stripe_module


from collections.abc import Generator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import BillingAccount, League, LeagueRole, Membership, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.routes.billing import provide_stripe_client

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


class StripeStub:
    def __init__(self) -> None:
        self.ensure_calls: list[tuple[str | None, str | None]] = []
        self.checkout_calls: list[dict[str, str]] = []
        self.portal_calls: list[dict[str, str]] = []
        self.customer_id = "cus_123"
        self.checkout_url = "https://stripe/checkout"
        self.portal_url = "https://stripe/portal"

    def ensure_customer(self, *, customer_id: str | None, email: str | None) -> str:
        self.ensure_calls.append((customer_id, email))
        return customer_id or self.customer_id

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        self.checkout_calls.append(
            {
                "customer_id": customer_id,
                "price_id": price_id,
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
        return self.checkout_url

    def create_billing_portal_session(self, *, customer_id: str, return_url: str) -> str:
        self.portal_calls.append({"customer_id": customer_id, "return_url": return_url})
        return self.portal_url


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    reset_database()
    get_settings.cache_clear()
    test_settings = Settings(
        APP_ENV="test",
        APP_URL="http://localhost:5173",
        API_URL="http://localhost:8000",
        DISCORD_CLIENT_ID="client",
        DISCORD_CLIENT_SECRET="secret",
        DISCORD_REDIRECT_URI="http://localhost:8000/auth/discord/callback",
        JWT_SECRET="test",
        JWT_ACCESS_TTL_MIN=15,
        JWT_REFRESH_TTL_DAYS=14,
        CORS_ORIGINS="http://localhost:5173",
        REDIS_URL="redis://localhost:6379/0",
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PRICE_PRO="price_pro",
        STRIPE_PRICE_ELITE="price_elite",
    )

    def get_test_session() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_session] = get_test_session

    yield

    app.dependency_overrides.clear()


@pytest.fixture()
def stripe_stub() -> Generator[StripeStub, None, None]:
    stub = StripeStub()
    app.dependency_overrides[provide_stripe_client] = lambda: stub
    try:
        yield stub
    finally:
        app.dependency_overrides.pop(provide_stripe_client, None)


@contextmanager
def override_user(user: User) -> Generator[None, None, None]:
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def create_user(session: Session, *, email: str | None = None) -> User:
    if email is None:
        email = f"{uuid4().hex}@example.com"
    user = User(discord_id=str(uuid4()), discord_username="user", email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_league(session: Session, *, owner: User) -> League:
    league = League(name="League", slug=f"league-{uuid4().hex[:8]}", owner_id=owner.id)
    session.add(league)
    session.commit()
    session.refresh(league)
    membership = Membership(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER)
    session.add(membership)
    session.commit()
    return league


class TestBillingRoutes:
    def test_checkout_updates_plan_and_returns_url(
        self,
        client: TestClient,
        stripe_stub: StripeStub,
    ) -> None:
        session = TestingSessionLocal()
        owner = create_user(session)
        create_league(session, owner=owner)

        with override_user(owner):
            response = client.post("/billing/checkout", json={"plan": "PRO"})

        assert response.status_code == 200, response.text
        assert response.json()["url"] == stripe_stub.checkout_url
        assert stripe_stub.checkout_calls
        # Billing account persisted
        stored = session.execute(
            select(BillingAccount).where(BillingAccount.owner_user_id == owner.id)
        ).scalar_one()
        assert stored.plan == "PRO"
        assert stored.stripe_customer_id == stripe_stub.customer_id
        league = session.execute(select(League).where(League.owner_id == owner.id)).scalar_one()
        assert league.plan == "PRO"
        assert league.driver_limit == 100
        session.close()

    def test_checkout_requires_owner(self, client: TestClient, stripe_stub: StripeStub) -> None:
        session = TestingSessionLocal()
        user = create_user(session)
        league = League(name="League", slug=f"league-{uuid4().hex[:8]}", owner_id=None)
        session.add(league)
        membership = Membership(league=league, user_id=user.id, role=LeagueRole.ADMIN)
        session.add(membership)
        session.commit()

        with override_user(user):
            response = client.post("/billing/checkout", json={"plan": "PRO"})

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "INSUFFICIENT_ROLE"
        session.close()

    def test_portal_requires_customer(self, client: TestClient, stripe_stub: StripeStub) -> None:
        session = TestingSessionLocal()
        owner = create_user(session)
        create_league(session, owner=owner)
        billing = BillingAccount(owner_user_id=owner.id, plan="FREE", stripe_customer_id=None)
        session.add(billing)
        session.commit()

        with override_user(owner):
            response = client.post("/billing/portal")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "BILLING_NOT_CONFIGURED"
        session.close()

    def test_portal_returns_url(self, client: TestClient, stripe_stub: StripeStub) -> None:
        session = TestingSessionLocal()
        owner = create_user(session)
        create_league(session, owner=owner)
        billing = BillingAccount(
            owner_user_id=owner.id, plan="PRO", stripe_customer_id="cus_existing"
        )
        session.add(billing)
        session.commit()

        with override_user(owner):
            response = client.post("/billing/portal")

        assert response.status_code == 200
        assert response.json()["url"] == stripe_stub.portal_url
        assert stripe_stub.portal_calls == [
            {"customer_id": "cus_existing", "return_url": "http://localhost:5173/billing"}
        ]
        session.close()
