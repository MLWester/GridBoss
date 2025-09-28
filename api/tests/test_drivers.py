from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from uuid import uuid4
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import BillingAccount, Driver, League, LeagueRole, Membership, Team, User
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


def create_league_with_owner(
    session: Session,
    owner: User,
    *,
    driver_limit: int = 20,
) -> League:
    league = League(
        name="Test League",
        slug=f"league-{uuid4().hex[:8]}",
        owner_id=owner.id,
        driver_limit=driver_limit,
    )
    session.add(league)
    session.commit()
    session.refresh(league)

    membership = Membership(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER)
    session.add(membership)
    session.commit()
    return league


def create_team(session: Session, league: League, name: str) -> Team:
    team = Team(league_id=league.id, name=name)
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


class TestDriverRoutes:
    def test_bulk_create_drivers_success(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner, driver_limit=10)
        team = create_team(database_session, league, "Alpha")

        payload = {
            "items": [
                {"display_name": "Driver One", "team_id": str(team.id)},
                {"display_name": "Driver Two"},
            ]
        }

        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/drivers", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert [item["display_name"] for item in data] == ["Driver One", "Driver Two"]
        assert data[0]["team_id"] == str(team.id)
        assert data[0]["team_name"] == "Alpha"
        assert data[1]["team_id"] is None
        assert data[1]["user_id"] is None
        assert data[1]["discord_id"] is None

        drivers = (
            database_session.execute(select(Driver).where(Driver.league_id == league.id))
            .scalars()
            .all()
        )
        assert len(drivers) == 2

    def test_bulk_create_drivers_duplicate_conflict(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        database_session.add(Driver(league_id=league.id, display_name="Driver One"))
        database_session.commit()

        payload = {"items": [{"display_name": "Driver One"}]}
        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/drivers", json=payload)

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["error"]["code"] == "DUPLICATE_DRIVER"

    def test_bulk_create_drivers_plan_limit(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner, driver_limit=1)

        payload = {
            "items": [
                {"display_name": "Driver One"},
                {"display_name": "Driver Two"},
            ]
        }

        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/drivers", json=payload)

        assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
        assert response.json()["error"]["code"] == "PLAN_LIMIT"

    def test_bulk_create_drivers_allows_during_grace(self, client: TestClient, database_session: Session) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner, driver_limit=1)
        league.plan = "FREE"
        database_session.commit()

        billing = BillingAccount(
            owner_user_id=owner.id,
            plan="FREE",
            plan_grace_plan="PRO",
            plan_grace_expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        database_session.add(billing)
        database_session.commit()

        payload = {
            "items": [
                {"display_name": "Driver One"},
                {"display_name": "Driver Two"},
            ]
        }

        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/drivers", json=payload)

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert len(data) == 2

    def test_bulk_create_drivers_denies_after_grace(self, client: TestClient, database_session: Session) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner, driver_limit=1)
        league.plan = "FREE"
        database_session.commit()

        billing = BillingAccount(
            owner_user_id=owner.id,
            plan="FREE",
            plan_grace_plan="PRO",
            plan_grace_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        database_session.add(billing)
        database_session.commit()

        payload = {
            "items": [
                {"display_name": "Driver One"},
                {"display_name": "Driver Two"},
            ]
        }

        with override_user(owner):
            response = client.post(f"/leagues/{league.id}/drivers", json=payload)

        assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
        assert response.json()["error"]["code"] == "PLAN_LIMIT"

    def test_update_driver_changes_name_and_team(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        team_alpha = create_team(database_session, league, "Alpha")
        team_beta = create_team(database_session, league, "Beta")

        driver = Driver(league_id=league.id, display_name="Driver One", team_id=team_alpha.id)
        database_session.add(driver)
        database_session.commit()
        database_session.refresh(driver)

        payload = {"display_name": "Driver Prime", "team_id": str(team_beta.id)}
        with override_user(owner):
            response = client.patch(f"/drivers/{driver.id}", json=payload)

        assert response.status_code == HTTPStatus.OK, response.text
        data = response.json()
        assert data["display_name"] == "Driver Prime"
        assert data["team_id"] == str(team_beta.id)
        assert data["team_name"] == "Beta"

    def test_update_driver_rejects_duplicate_name(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        driver1 = Driver(league_id=league.id, display_name="Driver One")
        driver2 = Driver(league_id=league.id, display_name="Driver Two")
        database_session.add_all([driver1, driver2])
        database_session.commit()
        database_session.refresh(driver2)

        with override_user(owner):
            response = client.patch(
                f"/drivers/{driver2.id}",
                json={"display_name": "Driver One"},
            )

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["error"]["code"] == "DUPLICATE_DRIVER"

    def test_delete_driver_requires_admin_role(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = stub_user(database_session, "steward")
        league = create_league_with_owner(database_session, owner)
        membership = Membership(
            league_id=league.id,
            user_id=steward.id,
            role=LeagueRole.STEWARD,
        )
        database_session.add(membership)
        driver = Driver(league_id=league.id, display_name="Driver One")
        database_session.add(driver)
        database_session.commit()
        database_session.refresh(driver)

        with override_user(steward):
            response = client.delete(f"/drivers/{driver.id}")

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json()["error"]["code"] == "INSUFFICIENT_ROLE"

    def test_list_drivers_returns_metadata(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        team = create_team(database_session, league, "Alpha")
        driver = Driver(
            league_id=league.id,
            display_name="Driver One",
            team_id=team.id,
            discord_id="1234",
        )
        database_session.add(driver)
        database_session.commit()

        with override_user(owner):
            response = client.get(f"/leagues/{league.id}/drivers")

        assert response.status_code == HTTPStatus.OK, response.text
        data = response.json()
        assert data[0]["team_name"] == "Alpha"
        assert data[0]["discord_id"] == "1234"
