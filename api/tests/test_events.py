from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from http import HTTPStatus
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import Event, EventStatus, League, LeagueRole, Membership, Season, User
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
    season = Season(league=league, name="Season", is_active=True)
    membership = Membership(league=league, user_id=owner.id, role=LeagueRole.OWNER)
    session.add_all([league, season, membership])
    session.commit()
    session.refresh(league)
    session.refresh(season)
    return league, season


def create_event(
    session: Session,
    *,
    league: League,
    season: Season,
    status: EventStatus = EventStatus.SCHEDULED,
    start_time: datetime | None = None,
) -> Event:
    event = Event(
        league_id=league.id,
        season_id=season.id,
        name=f"Event-{uuid4().hex[:6]}",
        track="Spa",
        start_time=start_time or datetime.now(UTC) + timedelta(days=1),
        status=status.value,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


class TestEventRoutes:
    def test_create_event_converts_to_utc(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)

        start_time = "2025-03-01T20:30:00-05:00"
        payload = {
            "name": "Night Race",
            "track": "Daytona",
            "start_time": start_time,
            "season_id": str(season.id),
            "laps": 200,
        }

        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/events", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        stored = database_session.get(Event, UUID(data["id"]))
        assert stored is not None
        expected_utc = datetime.fromisoformat("2025-03-02T01:30:00+00:00")
        stored_utc = stored.start_time.replace(tzinfo=UTC) if stored.start_time.tzinfo is None else stored.start_time
        assert stored_utc == expected_utc
    def test_list_events_with_timezone_filter(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        event = create_event(
            database_session,
            league=league,
            season=season,
            start_time=datetime(2025, 4, 10, 18, 0, tzinfo=UTC),
        )

        with override_user(owner):
            response = client.get(
                f"/leagues/{league.id}/events",
                params={"tz": "America/New_York"},
            )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) == 1
        converted = datetime.fromisoformat(data[0]["start_time"])
        expected_local = datetime(2025, 4, 10, 18, 0, tzinfo=UTC).astimezone(ZoneInfo('America/New_York'))
        assert converted == expected_local

    def test_status_filter_upcoming(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        create_event(
            database_session,
            league=league,
            season=season,
            start_time=datetime.now(UTC) + timedelta(days=2),
        )
        create_event(
            database_session,
            league=league,
            season=season,
            status=EventStatus.COMPLETED,
            start_time=datetime.now(UTC) - timedelta(days=1),
        )

        with override_user(owner):
            response = client.get(
                f"/leagues/{league.id}/events",
                params={"status": "upcoming"},
            )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == EventStatus.SCHEDULED.value

    def test_update_completed_event_blocked(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        event = create_event(
            database_session,
            league=league,
            season=season,
            status=EventStatus.COMPLETED,
        )

        with override_user(owner):
            response = client.patch(
                f"/events/{event.id}",
                json={"name": "Updated"},
            )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"]["code"] == "EVENT_COMPLETED"

    def test_cancel_event_sets_status(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        event = create_event(database_session, league=league, season=season)

        with override_user(owner):
            response = client.delete(f"/events/{event.id}")

        assert response.status_code == HTTPStatus.NO_CONTENT
        database_session.expire_all()
        refreshed = database_session.get(Event, event.id)
        assert refreshed.status == EventStatus.CANCELED.value

    def test_invalid_timezone_returns_error(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, _ = create_league_with_owner(database_session, owner)

        with override_user(owner):
            response = client.get(
                f"/leagues/{league.id}/events",
                params={"tz": "Mars/Olympus"},
            )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"]["code"] == "INVALID_TIMEZONE"

    def test_non_member_cannot_access(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        other = stub_user(database_session, "other")
        league, _ = create_league_with_owner(database_session, owner)

        with override_user(other):
            response = client.get(f"/leagues/{league.id}/events")

        assert response.status_code == HTTPStatus.FORBIDDEN




