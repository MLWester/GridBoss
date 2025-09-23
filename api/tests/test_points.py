from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import Event, League, LeagueRole, Membership, PointsScheme, Season, User
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


def create_event(session: Session, league: League, season: Season) -> Event:
    event = Event(
        league_id=league.id,
        season_id=season.id,
        name="Race 1",
        track="Spa",
        start_time=datetime.now(timezone.utc),
        status="SCHEDULED",
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


class TestPointsSchemeRoutes:
    def test_create_points_scheme_uses_default_rules(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)

        payload = {"name": "F1 Default", "season_id": str(season.id), "is_default": True}
        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/points-schemes", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert data["name"] == "F1 Default"
        assert len(data["rules"]) == 10
        assert data["rules"][0]["points"] == 25

    def test_create_points_scheme_custom_rules(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)

        rules = [{"position": 1, "points": 10}, {"position": 2, "points": 6}]
        payload = {
            "name": "Sprint",
            "season_id": str(season.id),
            "is_default": False,
            "rules": rules,
        }
        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/points-schemes", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert [rule["points"] for rule in data["rules"]] == [10, 6]

    def test_set_scheme_default_resets_previous(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)

        with override_user(owner):
            first = client.post(
                f"/leagues/{league.id}/points-schemes",
                json={"name": "Primary", "season_id": str(season.id), "is_default": True},
            )
            assert first.status_code == HTTPStatus.CREATED
            second = client.post(
                f"/leagues/{league.id}/points-schemes",
                json={"name": "Alternate", "season_id": str(season.id), "is_default": False},
            )
            assert second.status_code == HTTPStatus.CREATED

        scheme_id = UUID(second.json()["id"])
        with override_user(owner):
            response = client.patch(
                f"/points-schemes/{scheme_id}",
                json={"is_default": True},
            )

        assert response.status_code == HTTPStatus.OK
        defaults = (
            database_session.execute(
                select(PointsScheme).where(
                    PointsScheme.league_id == league.id,
                    PointsScheme.season_id == season.id,
                )
            )
            .scalars()
            .all()
        )
        default_flags = {scheme.name: scheme.is_default for scheme in defaults}
        assert default_flags == {"Primary": False, "Alternate": True}

    def test_delete_default_scheme_blocked_when_events_exist(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        create_event(database_session, league, season)

        with override_user(owner):
            response = client.post(
                f"/leagues/{league.id}/points-schemes",
                json={"name": "Protected", "season_id": str(season.id), "is_default": True},
            )
        assert response.status_code == HTTPStatus.CREATED
        scheme_id = response.json()["id"]

        with override_user(owner):
            delete_response = client.delete(f"/points-schemes/{scheme_id}")

        assert delete_response.status_code == HTTPStatus.BAD_REQUEST
        assert delete_response.json()["error"]["code"] == "SCHEME_IN_USE"

    def test_duplicate_positions_rejected(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        payload = {
            "name": "Invalid",
            "season_id": str(season.id),
            "is_default": False,
            "rules": [
                {"position": 1, "points": 10},
                {"position": 1, "points": 5},
            ],
        }

        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/points-schemes", json=payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"]["code"] == "DUPLICATE_POSITION"
