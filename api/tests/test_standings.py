from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from http import HTTPStatus
from uuid import uuid4

from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

if "dramatiq" not in sys.modules:
    class _ActorStub:
        def __init__(self, fn):
            self.fn = fn

        def send(self, *args, **kwargs):  # pragma: no cover - stub
            return None

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    def _actor(*args, **kwargs):
        def decorator(fn):
            return _ActorStub(fn)

        return decorator

    sys.modules["dramatiq"] = types.SimpleNamespace(actor=_actor)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
from app.services import standings as standings_service
from worker.jobs import standings as standings_jobs

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
    for table in Base.metadata.sorted_tables:
        for column in table.c:
            default = getattr(column, "server_default", None)
            if default is not None and hasattr(default, "arg") and "gen_random_uuid" in str(default.arg):
                column.server_default = None
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    get_settings.cache_clear()
    standings_service._cache_instance = None

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
    monkeypatch.setattr(standings_jobs.recompute_standings, "send", lambda *args, **kwargs: None)

    yield

    app.dependency_overrides.clear()
    standings_service._cache_instance = None


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


def create_driver(session: Session, league: League, *, display_name: str) -> Driver:
    driver = Driver(league_id=league.id, display_name=display_name)
    session.add(driver)
    session.commit()
    session.refresh(driver)
    return driver


def create_event(session: Session, league: League, season: Season, *, name: str) -> Event:
    event = Event(
        league_id=league.id,
        season_id=season.id,
        name=name,
        track="Test Track",
        start_time=datetime.now(UTC),
        status=EventStatus.SCHEDULED.value,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def record_result(
    session: Session,
    *,
    event: Event,
    driver: Driver,
    finish_position: int,
    total_points: int,
    bonus_points: int = 0,
    penalty_points: int = 0,
) -> Result:
    result = Result(
        event_id=event.id,
        driver_id=driver.id,
        finish_position=finish_position,
        started_position=finish_position,
        status=ResultStatus.FINISHED.value,
        bonus_points=bonus_points,
        penalty_points=penalty_points,
        total_points=total_points,
    )
    session.add(result)
    session.commit()
    session.refresh(result)
    return result


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


class TestStandingsRoutes:
    def test_standings_orders_by_points_wins_best_finish(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league, season = create_league_with_owner(database_session, owner)
        driver_a = create_driver(database_session, league, display_name="Driver A")
        driver_b = create_driver(database_session, league, display_name="Driver B")
        driver_c = create_driver(database_session, league, display_name="Driver C")

        event_one = create_event(database_session, league, season, name="Race 1")
        event_two = create_event(database_session, league, season, name="Race 2")
        event_one.status = EventStatus.COMPLETED.value
        event_two.status = EventStatus.COMPLETED.value
        database_session.commit()

        record_result(
            database_session,
            event=event_one,
            driver=driver_a,
            finish_position=1,
            total_points=25,
        )
        record_result(
            database_session,
            event=event_one,
            driver=driver_b,
            finish_position=2,
            total_points=15,
        )
        record_result(
            database_session,
            event=event_two,
            driver=driver_a,
            finish_position=3,
            total_points=10,
        )
        record_result(
            database_session,
            event=event_two,
            driver=driver_b,
            finish_position=2,
            total_points=20,
        )
        database_session.commit()

        with override_user(owner):
            response = client.get(
                f"/leagues/{league.id}/standings",
                params={"seasonId": str(season.id)},
            )
        assert response.status_code == HTTPStatus.OK, response.text
        data = response.json()
        assert data["season_id"] == str(season.id)
        items = data["items"]
        assert [item["driver_id"] for item in items] == [
            str(driver_a.id),
            str(driver_b.id),
            str(driver_c.id),
        ]
        assert items[0]["points"] == 35
        assert items[0]["wins"] == 1
        assert items[0]["best_finish"] == 1
        assert items[1]["points"] == 35
        assert items[1]["wins"] == 0
        assert items[1]["best_finish"] == 2
        assert items[2]["points"] == 0
        assert items[2]["wins"] == 0
        assert items[2]["best_finish"] is None

        with override_user(owner):
            default_response = client.get(f"/leagues/{league.id}/standings")
        assert default_response.status_code == HTTPStatus.OK
        assert default_response.json()["items"] == items

    def test_standings_requires_membership(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        outsider = stub_user(database_session, "outsider")
        league, season = create_league_with_owner(database_session, owner)

        event = create_event(database_session, league, season, name="Race 1")
        event.status = EventStatus.COMPLETED.value
        database_session.commit()

        record_result(
            database_session,
            event=event,
            driver=create_driver(database_session, league, display_name="Driver"),
            finish_position=1,
            total_points=25,
        )

        with override_user(outsider):
            response = client.get(
                f"/leagues/{league.id}/standings",
                params={"seasonId": str(season.id)},
            )
        assert response.status_code == HTTPStatus.FORBIDDEN
        payload = response.json()
        assert payload["error"]["code"] == "NOT_A_MEMBER"

    def test_standings_cache_invalidation_on_results_update(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = owner
        league, season = create_league_with_owner(database_session, owner)
        driver_a = create_driver(database_session, league, display_name="Driver A")
        driver_b = create_driver(database_session, league, display_name="Driver B")

        event = create_event(database_session, league, season, name="Race 1")
        seed_points_scheme(database_session, league, season)

        initial_payload = {
            "entries": [
                {
                    "driver_id": str(driver_a.id),
                    "finish_position": 1,
                    "started_position": 1,
                    "status": "FINISHED",
                    "bonus_points": 0,
                    "penalty_points": 0,
                },
                {
                    "driver_id": str(driver_b.id),
                    "finish_position": 2,
                    "started_position": 2,
                    "status": "FINISHED",
                    "bonus_points": 0,
                    "penalty_points": 0,
                },
            ]
        }

        with override_user(steward):
            post_response = client.post(
                f"/events/{event.id}/results",
                json=initial_payload,
                headers={"Idempotency-Key": uuid4().hex},
            )
        assert post_response.status_code == HTTPStatus.CREATED, post_response.text

        with override_user(owner):
            first_standings = client.get(
                f"/leagues/{league.id}/standings",
                params={"seasonId": str(season.id)},
            )
        assert first_standings.status_code == HTTPStatus.OK
        first_payload = first_standings.json()

        result_b = database_session.execute(
            select(Result).where(Result.event_id == event.id, Result.driver_id == driver_b.id)
        ).scalar_one()
        result_b.total_points = 99
        database_session.commit()

        with override_user(owner):
            cached_response = client.get(
                f"/leagues/{league.id}/standings",
                params={"seasonId": str(season.id)},
            )
        assert cached_response.status_code == HTTPStatus.OK
        assert cached_response.json() == first_payload

        update_payload = {
            "entries": [
                {
                    "driver_id": str(driver_a.id),
                    "finish_position": 2,
                    "started_position": 2,
                    "status": "FINISHED",
                    "bonus_points": 0,
                    "penalty_points": 8,
                },
                {
                    "driver_id": str(driver_b.id),
                    "finish_position": 1,
                    "started_position": 1,
                    "status": "FINISHED",
                    "bonus_points": 5,
                    "penalty_points": 0,
                },
            ]
        }

        with override_user(steward):
            update_response = client.post(
                f"/events/{event.id}/results",
                json=update_payload,
                headers={"Idempotency-Key": uuid4().hex},
            )
        assert update_response.status_code == HTTPStatus.CREATED, update_response.text

        with override_user(owner):
            refreshed = client.get(
                f"/leagues/{league.id}/standings",
                params={"seasonId": str(season.id)},
            )
        assert refreshed.status_code == HTTPStatus.OK
        refreshed_payload = refreshed.json()
        assert refreshed_payload != first_payload
        refreshed_items = refreshed_payload["items"]
        assert refreshed_items[0]["driver_id"] == str(driver_b.id)
        assert refreshed_items[0]["points"] == 30
        assert refreshed_items[1]["driver_id"] == str(driver_a.id)
        assert refreshed_items[1]["points"] == 10



