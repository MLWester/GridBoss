from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import AuditLog, BillingAccount, DiscordIntegration, League, LeagueRole, Membership, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.routes.auth import provide_discord_client
from worker.jobs import discord as discord_jobs

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


class StubDiscordClient:
    def __init__(self) -> None:  # pragma: no cover
        pass


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    for table in Base.metadata.sorted_tables:
        for column in table.c:
            default = getattr(column, "server_default", None)
            if default is not None and hasattr(default, "arg") and "gen_random_uuid" in str(default.arg):
                column.server_default = None
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    get_settings.cache_clear()

    test_settings = Settings(
        APP_ENV="test",
        APP_URL="http://localhost:5173",
        API_URL="http://localhost:8000",
        DISCORD_CLIENT_ID="client",
        DISCORD_CLIENT_SECRET="secret",  # noqa: S106
        DISCORD_REDIRECT_URI="http://localhost:8000/auth/discord/callback",
        JWT_SECRET="test-secret",  # noqa: S106
        JWT_ACCESS_TTL_MIN=15,
        JWT_REFRESH_TTL_DAYS=14,
        CORS_ORIGINS="http://localhost:5173",
        REDIS_URL="redis://localhost:6379/0",
    )

    app.dependency_overrides[get_settings] = lambda: test_settings

    def get_test_session() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[provide_discord_client] = lambda: StubDiscordClient()

    yield

    app.dependency_overrides.clear()


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


@pytest.fixture()
def database_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def job_spy(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[str, ...], dict[str, str]]]:
    calls: list[tuple[tuple[str, ...], dict[str, str]]] = []

    def _record(*args: str, **kwargs: str) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(discord_jobs.send_test_message, "send", _record)
    return calls


def create_user(session: Session, discord_id: str) -> User:
    user = User(discord_id=discord_id, discord_username=discord_id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_league(
    session: Session,
    *,
    owner: User,
    plan: str,
) -> League:
    league = League(name="League", slug=f"league-{uuid4().hex[:8]}", owner_id=owner.id, plan=plan)
    session.add(league)
    session.commit()
    session.refresh(league)
    membership = Membership(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER)
    session.add(membership)
    session.commit()
    return league


def add_member(
    session: Session,
    *,
    league: League,
    user: User,
    role: LeagueRole,
) -> Membership:
    membership = Membership(league_id=league.id, user_id=user.id, role=role)
    session.add(membership)
    session.commit()
    session.refresh(membership)
    return membership


class TestDiscordIntegrationRoutes:
    def test_link_discord_creates_integration(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = create_user(database_session, "owner")
        admin = create_user(database_session, "admin")
        league = create_league(database_session, owner=owner, plan="PRO")
        add_member(database_session, league=league, user=admin, role=LeagueRole.ADMIN)

        payload = {"guild_id": "123", "channel_id": "456"}
        with override_user(admin):
            response = client.post(f"/leagues/{league.id}/discord/link", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert data["guild_id"] == "123"
        assert data["channel_id"] == "456"
        assert data["installed_by_user"] == str(admin.id)

        integration = database_session.execute(
            select(DiscordIntegration).where(DiscordIntegration.league_id == league.id)
        ).scalar_one()
        assert integration.guild_id == "123"
        assert integration.channel_id == "456"
        assert integration.installed_by_user == admin.id
        assert integration.is_active is True

        audit = database_session.execute(
            select(AuditLog).where(AuditLog.action == "link", AuditLog.league_id == league.id)
        ).scalar_one()
        assert audit.entity == "discord_integration"
        assert audit.entity_id == str(integration.id)

    def test_link_requires_admin_role(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = create_user(database_session, "owner")
        steward = create_user(database_session, "steward")
        league = create_league(database_session, owner=owner, plan="PRO")
        add_member(database_session, league=league, user=steward, role=LeagueRole.STEWARD)

        with override_user(steward):
            response = client.post(
                f"/leagues/{league.id}/discord/link",
                json={"guild_id": "123", "channel_id": "456"},
            )

        assert response.status_code == HTTPStatus.FORBIDDEN
        payload = response.json()
        assert payload["error"]["code"] == "INSUFFICIENT_ROLE"

    def test_link_requires_pro_plan(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = create_user(database_session, "owner")
        admin = create_user(database_session, "admin")
        league = create_league(database_session, owner=owner, plan="FREE")
        add_member(database_session, league=league, user=admin, role=LeagueRole.ADMIN)

        with override_user(admin):
            response = client.post(
                f"/leagues/{league.id}/discord/link",
                json={"guild_id": "123", "channel_id": "456"},
            )

        assert response.status_code == HTTPStatus.FORBIDDEN
        payload = response.json()
        assert payload["error"]["code"] == "PLAN_LIMIT"

    def test_link_allows_during_plan_grace(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = create_user(database_session, "owner")
        admin = create_user(database_session, "admin")
        league = create_league(database_session, owner=owner, plan="FREE")
        add_member(database_session, league=league, user=admin, role=LeagueRole.ADMIN)

        grace_expiration = datetime.now(timezone.utc) + timedelta(days=3)
        billing = BillingAccount(
            owner_user_id=owner.id,
            plan="FREE",
            plan_grace_plan="PRO",
            plan_grace_expires_at=grace_expiration,
        )
        database_session.add(billing)
        database_session.commit()

        payload = {"guild_id": "123", "channel_id": "456"}
        with override_user(admin):
            response = client.post(f"/leagues/{league.id}/discord/link", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text

    def test_link_requires_plan_after_grace_expires(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = create_user(database_session, "owner")
        admin = create_user(database_session, "admin")
        league = create_league(database_session, owner=owner, plan="FREE")
        add_member(database_session, league=league, user=admin, role=LeagueRole.ADMIN)

        billing = BillingAccount(
            owner_user_id=owner.id,
            plan="FREE",
            plan_grace_plan="PRO",
            plan_grace_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        database_session.add(billing)
        database_session.commit()

        payload = {"guild_id": "123", "channel_id": "456"}
        with override_user(admin):
            response = client.post(f"/leagues/{league.id}/discord/link", json=payload)

        assert response.status_code == HTTPStatus.FORBIDDEN
        data = response.json()
        assert data["error"]["code"] == "PLAN_LIMIT"

    def test_test_endpoint_enqueues_job(
        self,
        client: TestClient,
        database_session: Session,
        job_spy: list[tuple[tuple[str, ...], dict[str, str]]],
    ) -> None:
        owner = create_user(database_session, "owner")
        admin = create_user(database_session, "admin")
        league = create_league(database_session, owner=owner, plan="PRO")
        add_member(database_session, league=league, user=admin, role=LeagueRole.ADMIN)

        with override_user(admin):
            link_response = client.post(
                f"/leagues/{league.id}/discord/link",
                json={"guild_id": "guild", "channel_id": "channel"},
            )
        assert link_response.status_code == HTTPStatus.CREATED

        with override_user(admin):
            test_response = client.post(f"/leagues/{league.id}/discord/test")

        assert test_response.status_code == HTTPStatus.ACCEPTED, test_response.text
        assert test_response.json()["status"] == "queued"

        assert job_spy == [((str(league.id), "guild", "channel"), {})]

        audit_actions = database_session.execute(
            select(AuditLog.action).where(AuditLog.league_id == league.id)
        ).scalars().all()
        assert "test" in audit_actions

    def test_test_endpoint_requires_active_integration(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = create_user(database_session, "owner")
        admin = create_user(database_session, "admin")
        league = create_league(database_session, owner=owner, plan="PRO")
        add_member(database_session, league=league, user=admin, role=LeagueRole.ADMIN)

        integration = DiscordIntegration(
            league_id=league.id,
            guild_id="guild",
            channel_id="channel",
            installed_by_user=admin.id,
            is_active=False,
        )
        database_session.add(integration)
        database_session.commit()

        with override_user(admin):
            response = client.post(f"/leagues/{league.id}/discord/test")

        assert response.status_code == HTTPStatus.CONFLICT
        payload = response.json()
        assert payload["error"]["code"] == "INTEGRATION_INACTIVE"

    def test_test_endpoint_requires_link(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = create_user(database_session, "owner")
        admin = create_user(database_session, "admin")
        league = create_league(database_session, owner=owner, plan="PRO")
        add_member(database_session, league=league, user=admin, role=LeagueRole.ADMIN)

        with override_user(admin):
            response = client.post(f"/leagues/{league.id}/discord/test")

        assert response.status_code == HTTPStatus.NOT_FOUND
        payload = response.json()
        assert payload["error"]["code"] == "DISCORD_NOT_LINKED"

