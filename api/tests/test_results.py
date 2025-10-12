from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from worker.jobs import standings

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import (
    Driver,
    Event,
    EventStatus,
    League,
    LeagueRole,
    Membership,
    PointsRule,
    PointsScheme,
    Result,
    ResultStatus,
    Season,
    User,
)
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

    monkeypatch.setattr(standings.recompute_standings, "send", lambda *args, **kwargs: None)

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


def create_driver(
    session: Session, league: League, user: User | None = None, *, display_name: str
) -> Driver:
    driver = Driver(
        league_id=league.id,
        user_id=user.id if user else None,
        display_name=display_name,
    )
    session.add(driver)
    session.commit()
    session.refresh(driver)
    return driver


def create_event(session: Session, league: League, season: Season) -> Event:
    event = Event(
        league_id=league.id,
        season_id=season.id,
        name="Race 1",
        track="Spa",
        start_time=datetime.now(UTC),
        status=EventStatus.SCHEDULED.value,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def seed_points_scheme(session: Session, league: League, season: Season) -> PointsScheme:
    scheme = PointsScheme(
        league_id=league.id,
        season_id=season.id,
        name="Default",
        is_default=True,
    )
    rules = [
        PointsRule(position=1, points=25),
        PointsRule(position=2, points=18),
        PointsRule(position=3, points=15),
        PointsRule(position=4, points=12),
    ]
    scheme.rules = rules
    session.add(scheme)
    session.commit()
    session.refresh(scheme)
    return scheme


class TestResultsRoutes:
    def test_submit_results_success(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = stub_user(database_session, "steward")
        league, season = create_league_with_owner(database_session, owner)
        membership = Membership(league_id=league.id, user_id=steward.id, role=LeagueRole.STEWARD)
        database_session.add(membership)
        driver1 = create_driver(database_session, league, display_name="Driver 1")
        driver2 = create_driver(database_session, league, display_name="Driver 2")
        event = create_event(database_session, league, season)
        seed_points_scheme(database_session, league, season)

        payload = {
            "entries": [
                {
                    "driver_id": str(driver1.id),
                    "finish_position": 1,
                    "started_position": 2,
                    "bonus_points": 1,
                    "penalty_points": 0,
                },
                {
                    "driver_id": str(driver2.id),
                    "finish_position": 2,
                    "started_position": 1,
                    "bonus_points": 0,
                    "penalty_points": 0,
                },
            ]
        }

        with override_user(steward):
            response = client.post(
                f"/events/{event.id}/results",
                json=payload,
                headers={"Idempotency-Key": "abc123"},
            )

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert data["event_id"] == str(event.id)
        totals = {item["driver_id"]: item["total_points"] for item in data["items"]}
        assert totals[str(driver1.id)] == 26  # 25 base + 1 bonus
        assert totals[str(driver2.id)] == 18

        database_session.refresh(event)
        refreshed_event = database_session.get(Event, event.id)
        assert refreshed_event.status == EventStatus.COMPLETED.value

    def test_idempotent_duplicate_same_payload(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = stub_user(database_session, "steward")
        league, season = create_league_with_owner(database_session, owner)
        membership = Membership(league_id=league.id, user_id=steward.id, role=LeagueRole.STEWARD)
        database_session.add(membership)
        driver1 = create_driver(database_session, league, display_name="Driver 1")
        driver2 = create_driver(database_session, league, display_name="Driver 2")
        event = create_event(database_session, league, season)
        seed_points_scheme(database_session, league, season)

        payload = {
            "entries": [
                {
                    "driver_id": str(driver1.id),
                    "finish_position": 1,
                    "bonus_points": 0,
                    "penalty_points": 0,
                },
                {
                    "driver_id": str(driver2.id),
                    "finish_position": 2,
                    "bonus_points": 0,
                    "penalty_points": 0,
                },
            ]
        }

        with override_user(steward):
            first = client.post(
                f"/events/{event.id}/results",
                json=payload,
                headers={"Idempotency-Key": "dup-key"},
            )
            second = client.post(
                f"/events/{event.id}/results",
                json=payload,
                headers={"Idempotency-Key": "dup-key"},
            )

        assert first.status_code == HTTPStatus.CREATED
        assert second.status_code == HTTPStatus.CREATED
        assert second.json()["items"] == first.json()["items"]

    def test_idempotent_conflict(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = stub_user(database_session, "steward")
        league, season = create_league_with_owner(database_session, owner)
        membership = Membership(league_id=league.id, user_id=steward.id, role=LeagueRole.STEWARD)
        database_session.add(membership)
        driver1 = create_driver(database_session, league, display_name="Driver 1")
        driver2 = create_driver(database_session, league, display_name="Driver 2")
        event = create_event(database_session, league, season)
        seed_points_scheme(database_session, league, season)

        payload_one = {
            "entries": [
                {"driver_id": str(driver1.id), "finish_position": 1},
                {"driver_id": str(driver2.id), "finish_position": 2},
            ]
        }
        payload_two = {
            "entries": [
                {"driver_id": str(driver1.id), "finish_position": 1},
                {"driver_id": str(driver2.id), "finish_position": 3},
            ]
        }

        with override_user(steward):
            client.post(
                f"/events/{event.id}/results",
                json=payload_one,
                headers={"Idempotency-Key": "dup-key"},
            )
            conflict = client.post(
                f"/events/{event.id}/results",
                json=payload_two,
                headers={"Idempotency-Key": "dup-key"},
            )

        assert conflict.status_code == HTTPStatus.CONFLICT
        assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

    def test_get_results(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        driver1 = create_driver(database_session, league, display_name="Driver 1")
        driver2 = create_driver(database_session, league, display_name="Driver 2")
        event = create_event(database_session, league, season)

        result1 = Result(
            event_id=event.id,
            driver_id=driver1.id,
            finish_position=1,
            bonus_points=0,
            penalty_points=0,
            total_points=10,
            status=ResultStatus.FINISHED.value,
        )
        result2 = Result(
            event_id=event.id,
            driver_id=driver2.id,
            finish_position=2,
            bonus_points=0,
            penalty_points=0,
            total_points=8,
            status=ResultStatus.FINISHED.value,
        )
        database_session.add_all([result1, result2])
        database_session.commit()

        with override_user(owner):
            response = client.get(f"/events/{event.id}/results")

        assert response.status_code == HTTPStatus.OK
        payload = response.json()
        assert len(payload["items"]) == 2

    def test_requires_steward_role(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        driver_user = stub_user(database_session, "driver")
        league, season = create_league_with_owner(database_session, owner)
        membership = Membership(league_id=league.id, user_id=driver_user.id, role=LeagueRole.DRIVER)
        database_session.add(membership)
        driver1 = create_driver(database_session, league, display_name="Driver 1")
        driver2 = create_driver(database_session, league, display_name="Driver 2")
        event = create_event(database_session, league, season)

        payload = {
            "entries": [
                {"driver_id": str(driver1.id), "finish_position": 1},
                {"driver_id": str(driver2.id), "finish_position": 2},
            ]
        }

        with override_user(driver_user):
            response = client.post(f"/events/{event.id}/results", json=payload)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_invalid_driver_rejected(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = stub_user(database_session, "steward")
        league, season = create_league_with_owner(database_session, owner)
        membership = Membership(league_id=league.id, user_id=steward.id, role=LeagueRole.STEWARD)
        database_session.add(membership)
        event = create_event(database_session, league, season)

        payload = {
            "entries": [
                {"driver_id": str(uuid4()), "finish_position": 1},
            ]
        }

        with override_user(steward):
            response = client.post(f"/events/{event.id}/results", json=payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"]["code"].startswith("MISSING_DRIVER")

    def test_duplicate_finish_position_rejected(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = stub_user(database_session, "steward")
        league, season = create_league_with_owner(database_session, owner)
        membership = Membership(league_id=league.id, user_id=steward.id, role=LeagueRole.STEWARD)
        database_session.add(membership)
        driver1 = create_driver(database_session, league, display_name="Driver 1")
        driver2 = create_driver(database_session, league, display_name="Driver 2")
        event = create_event(database_session, league, season)

        payload = {
            "entries": [
                {"driver_id": str(driver1.id), "finish_position": 1},
                {"driver_id": str(driver2.id), "finish_position": 1},
            ]
        }

        with override_user(steward):
            response = client.post(f"/events/{event.id}/results", json=payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"]["code"] == "DUPLICATE_POSITION"
