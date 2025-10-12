from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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


def create_league_with_owner(session: Session, owner: User) -> tuple[League, Season]:
    league = League(
        name="Test League",
        slug=f"league-{uuid4().hex[:8]}",
        owner_id=owner.id,
    )
    season = Season(league=league, name="Initial Season", is_active=True)
    membership = Membership(league=league, user_id=owner.id, role=LeagueRole.OWNER)
    session.add_all([league, season, membership])
    session.commit()
    session.refresh(league)
    session.refresh(season)
    return league, season


class TestSeasonRoutes:
    def test_create_season_inactive_preserves_existing_active(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, active_season = create_league_with_owner(database_session, owner)

        payload = {"name": "Winter Series", "is_active": False}
        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/seasons", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert data["name"] == "Winter Series"
        assert data["is_active"] is False

        refreshed_active = database_session.get(Season, active_season.id)
        assert refreshed_active.is_active is True

    def test_create_season_active_swaps_previous(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, active_season = create_league_with_owner(database_session, owner)

        payload = {"name": "Spring Series", "is_active": True}
        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/seasons", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        new_season_id = UUID(response.json()["id"])

        database_session.expire_all()
        old = database_session.get(Season, active_season.id)
        new = database_session.get(Season, new_season_id)
        assert old.is_active is False
        assert new.is_active is True

    def test_update_season_activate(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, active_season = create_league_with_owner(database_session, owner)

        inactive_season = Season(league_id=league.id, name="Off Season", is_active=False)
        database_session.add(inactive_season)
        database_session.commit()
        database_session.refresh(inactive_season)

        with override_user(owner):
            response = client.patch(
                f"/seasons/{inactive_season.id}",
                json={"is_active": True},
            )

        assert response.status_code == HTTPStatus.OK, response.text
        database_session.refresh(active_season)
        database_session.refresh(inactive_season)
        assert inactive_season.is_active is True
        assert active_season.is_active is False

    def test_update_season_cannot_deactivate_last_active(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, active_season = create_league_with_owner(database_session, owner)

        with override_user(owner):
            response = client.patch(
                f"/seasons/{active_season.id}",
                json={"is_active": False},
            )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"]["code"] == "LAST_ACTIVE_SEASON"

    def test_list_seasons_returns_all(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, _ = create_league_with_owner(database_session, owner)
        database_session.add(Season(league_id=league.id, name="Second Season", is_active=False))
        database_session.commit()

        with override_user(owner):
            response = client.get(f"/leagues/{league.id}/seasons")

        assert response.status_code == HTTPStatus.OK
        names = {item["name"] for item in response.json()}
        assert names == {"Initial Season", "Second Season"}
