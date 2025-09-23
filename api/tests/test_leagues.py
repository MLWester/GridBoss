from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import League, LeagueRole, Membership, Season, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.routes.auth import provide_discord_client

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

    async def exchange_code(self, *, code: str, code_verifier: str) -> dict[str, str]:
        return {"access_token": "token"}

    async def fetch_user(self, *, access_token: str) -> dict[str, str]:
        return {
            "id": "123",
            "username": "Stub",
            "avatar": None,
            "email": None,
        }


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def override_dependencies() -> Generator[None, None, None]:
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


def stub_user(session: Session, discord_id: str) -> User:
    user = User(discord_id=discord_id, discord_username=discord_id)
    session.add(user)
    session.commit()
    return user


class TestLeaguesRoutes:
    def test_create_league_creates_season_and_membership(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        with override_user(owner):
            response = client.post(
                "/leagues",
                json={"name": "Summer Series", "slug": "summer-series"},
            )
        assert response.status_code == HTTPStatus.CREATED, response.text
        league_id = UUID(response.json()["id"])

        membership = database_session.execute(
            select(Membership).where(Membership.league_id == league_id)
        ).scalar_one_or_none()
        assert membership is not None
        assert membership.role == LeagueRole.OWNER

        season = database_session.execute(
            select(Season).where(Season.league_id == league_id)
        ).scalar_one_or_none()
        assert season is not None

    def test_slug_conflict_returns_409(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        with override_user(owner):
            client.post("/leagues", json={"name": "League", "slug": "conflict"})
            response = client.post("/leagues", json={"name": "Other", "slug": "conflict"})
        assert response.status_code == HTTPStatus.CONFLICT

    def test_list_leagues_filters_deleted(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        with override_user(owner):
            create_resp = client.post("/leagues", json={"name": "Active", "slug": "active"})
        league_id = UUID(create_resp.json()["id"])

        league = database_session.get(League, league_id)
        league.is_deleted = True
        database_session.commit()

        with override_user(owner):
            list_resp = client.get("/leagues")
        assert list_resp.status_code == HTTPStatus.OK
        assert list_resp.json() == []

    def test_owner_can_update_league(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        with override_user(owner):
            create_resp = client.post(
                "/leagues",
                json={"name": "League", "slug": "league-1"},
            )
        league_id = UUID(create_resp.json()["id"])

        with override_user(owner):
            patch_resp = client.patch(
                f"/leagues/{league_id}",
                json={"name": "Updated"},
            )
        assert patch_resp.status_code == HTTPStatus.OK
        assert patch_resp.json()["name"] == "Updated"

    def test_non_owner_cannot_update_or_delete(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        other = stub_user(database_session, "other")
        with override_user(owner):
            create_resp = client.post(
                "/leagues",
                json={"name": "League", "slug": "league"},
            )
        league_id = UUID(create_resp.json()["id"])

        database_session.add(
            Membership(league_id=league_id, user_id=other.id, role=LeagueRole.ADMIN)
        )
        database_session.commit()

        with override_user(other):
            patch_resp = client.patch(
                f"/leagues/{league_id}",
                json={"name": "Nope"},
            )
        assert patch_resp.status_code == HTTPStatus.FORBIDDEN

        with override_user(other):
            delete_resp = client.delete(f"/leagues/{league_id}")
        assert delete_resp.status_code == HTTPStatus.FORBIDDEN

    def test_owner_can_soft_delete(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        with override_user(owner):
            create_resp = client.post(
                "/leagues",
                json={"name": "League", "slug": "delete-me"},
            )
        league_id = UUID(create_resp.json()["id"])

        with override_user(owner):
            delete_resp = client.delete(f"/leagues/{league_id}")
        assert delete_resp.status_code == HTTPStatus.NO_CONTENT

        league = database_session.get(League, league_id)
        assert league.is_deleted is True
        assert league.deleted_at is not None
