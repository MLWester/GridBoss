from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import (
    AuditLog,
    BillingAccount,
    DiscordIntegration,
    League,
    LeagueRole,
    Membership,
    Subscription,
    User,
)
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.services.plan import PLAN_DRIVER_LIMITS

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
def override_dependencies(monkeypatch: pytest.MonkeyPatch) -> Generator[Settings, None, None]:
    reset_database()
    get_settings.cache_clear()
    test_settings = Settings(
        APP_ENV="development",
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
        ADMIN_MODE=True,
    )

    def get_test_session() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_session] = get_test_session

    yield test_settings

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@contextmanager
def override_user(user: User) -> Generator[None, None, None]:
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def create_user(session: Session, *, email: str | None = None, is_founder: bool = False) -> User:
    if email is None:
        email = f"{uuid4().hex[:8]}@example.com"
    user = User(
        discord_id=str(uuid4()),
        discord_username=f"user-{uuid4().hex[:6]}",
        email=email,
        is_active=True,
        is_founder=is_founder,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_league(session: Session, *, owner: User, name: str = "Demo League") -> League:
    league = League(
        name=name, slug=f"{name.lower().replace(' ', '-')}-{uuid4().hex[:6]}", owner_id=owner.id
    )
    session.add(league)
    session.commit()
    session.refresh(league)
    membership = Membership(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER)
    session.add(membership)
    session.commit()
    return league


def create_billing_account(session: Session, owner: User, plan: str = "FREE") -> BillingAccount:
    account = BillingAccount(
        owner_user_id=owner.id, plan=plan, stripe_customer_id=f"cus_{uuid4().hex[:6]}"
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def create_subscription(
    session: Session, account: BillingAccount, status: str = "active"
) -> Subscription:
    subscription = Subscription(
        billing_account_id=account.id,
        plan=account.plan,
        status=status,
        stripe_subscription_id=f"sub_{uuid4().hex[:6]}",
    )
    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return subscription


class TestAdminConsole:
    def test_search_requires_founder(
        self, client: TestClient, override_dependencies: Settings
    ) -> None:
        session = TestingSessionLocal()
        user = create_user(session, is_founder=False)
        with override_user(user):
            response = client.get("/admin/search")
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "FOUNDER_ACCESS_REQUIRED"
        session.close()

    def test_search_returns_users_and_leagues(self, client: TestClient) -> None:
        session = TestingSessionLocal()
        founder = create_user(session, is_founder=True)
        owner = create_user(session, email="owner@example.com")
        league = create_league(session, owner=owner, name="Velocity League")
        account = create_billing_account(session, owner=owner, plan="PRO")
        create_subscription(session, account, status="active")
        integration = DiscordIntegration(
            league_id=league.id,
            guild_id="guild",
            channel_id="channel",
            installed_by_user=owner.id,
            is_active=True,
        )
        session.add(integration)
        session.commit()

        with override_user(founder):
            response = client.get("/admin/search", params={"query": "Velocity"})

        assert response.status_code == 200
        payload = response.json()
        assert any(user["email"] == "owner@example.com" for user in payload["users"])
        assert any(league_item["name"] == "Velocity League" for league_item in payload["leagues"])
        session.close()

    def test_toggle_discord_integration(self, client: TestClient) -> None:
        session = TestingSessionLocal()
        founder = create_user(session, is_founder=True)
        owner = create_user(session)
        league = create_league(session, owner=owner)
        integration = DiscordIntegration(
            league_id=league.id,
            guild_id="guild",
            channel_id="channel",
            installed_by_user=owner.id,
            is_active=False,
        )
        session.add(integration)
        session.commit()

        with override_user(founder):
            response = client.post(
                f"/admin/leagues/{league.id}/discord/toggle",
                json={"is_active": True},
            )

        assert response.status_code == 200
        session.refresh(integration)
        assert integration.is_active is True
        session.close()

    def test_plan_override_updates_leagues_and_billing(self, client: TestClient) -> None:
        session = TestingSessionLocal()
        founder = create_user(session, is_founder=True)
        owner = create_user(session)
        primary_league = create_league(session, owner=owner, name="Primary")
        secondary_league = create_league(session, owner=owner, name="Secondary")
        account = create_billing_account(session, owner=owner, plan="FREE")

        with override_user(founder):
            response = client.post(
                f"/admin/leagues/{primary_league.id}/plan",
                json={"plan": "PRO"},
            )

        assert response.status_code == 200
        session.refresh(primary_league)
        session.refresh(secondary_league)
        session.refresh(account)

        assert primary_league.plan == "PRO"
        assert primary_league.driver_limit == PLAN_DRIVER_LIMITS["PRO"]
        assert secondary_league.plan == "PRO"
        assert account.plan == "PRO"

        audit_count = session.execute(select(func.count(AuditLog.id))).scalar_one()
        assert audit_count >= 2
        session.close()

    def test_plan_override_disabled_in_production(
        self,
        client: TestClient,
        override_dependencies: Settings,
    ) -> None:
        session = TestingSessionLocal()
        founder = create_user(session, is_founder=True)
        owner = create_user(session)
        league = create_league(session, owner=owner)

        override_dependencies.app_env = "production"

        with override_user(founder):
            response = client.post(
                f"/admin/leagues/{league.id}/plan",
                json={"plan": "PRO"},
            )

        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "PLAN_OVERRIDE_DISABLED"
        session.close()
