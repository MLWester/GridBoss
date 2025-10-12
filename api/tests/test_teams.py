from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import Driver, League, LeagueRole, Membership, Team, User
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


def create_league_with_owner(session: Session, owner: User) -> League:
    league = League(
        name="Test League",
        slug=f"league-{uuid4().hex[:8]}",
        owner_id=owner.id,
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


class TestTeamRoutes:
    def test_create_team_success(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)

        with override_user(owner):
            response = client.post(
                f"/leagues/{league.id}/teams",
                json={"name": "Alpha"},
            )

        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert data["name"] == "Alpha"
        assert data["driver_count"] == 0

    def test_create_team_duplicate_name(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        create_team(database_session, league, "Alpha")

        with override_user(owner):
            response = client.post(
                f"/leagues/{league.id}/teams",
                json={"name": "Alpha"},
            )

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["error"]["code"] == "DUPLICATE_TEAM"

    def test_update_team_changes_name(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        team = create_team(database_session, league, "Alpha")

        with override_user(owner):
            response = client.patch(
                f"/teams/{team.id}",
                json={"name": "Beta"},
            )

        assert response.status_code == HTTPStatus.OK, response.text
        assert response.json()["name"] == "Beta"

    def test_delete_team_reassigns_drivers(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        team = create_team(database_session, league, "Alpha")
        driver = Driver(league_id=league.id, display_name="Driver One", team_id=team.id)
        database_session.add(driver)
        database_session.commit()
        database_session.refresh(driver)
        driver_id = driver.id

        with override_user(owner):
            response = client.delete(f"/teams/{team.id}")

        assert response.status_code == HTTPStatus.NO_CONTENT, response.text
        database_session.expire_all()
        reloaded = database_session.get(Driver, driver_id)
        assert reloaded is not None
        assert reloaded.team_id is None

    def test_list_teams_includes_driver_counts(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        league = create_league_with_owner(database_session, owner)
        team_alpha = create_team(database_session, league, "Alpha")
        team_beta = create_team(database_session, league, "Beta")
        database_session.add_all(
            [
                Driver(league_id=league.id, display_name="Driver One", team_id=team_alpha.id),
                Driver(league_id=league.id, display_name="Driver Two", team_id=team_alpha.id),
                Driver(league_id=league.id, display_name="Driver Three", team_id=team_beta.id),
            ]
        )
        database_session.commit()

        with override_user(owner):
            response = client.get(f"/leagues/{league.id}/teams")

        assert response.status_code == HTTPStatus.OK, response.text
        data = response.json()
        counts = {item["name"]: item["driver_count"] for item in data}
        assert counts["Alpha"] == 2
        assert counts["Beta"] == 1

    def test_modify_team_requires_admin(
        self,
        client: TestClient,
        database_session: Session,
    ) -> None:
        owner = stub_user(database_session, "owner")
        steward = stub_user(database_session, "steward")
        league = create_league_with_owner(database_session, owner)
        team = create_team(database_session, league, "Alpha")
        membership = Membership(
            league_id=league.id,
            user_id=steward.id,
            role=LeagueRole.STEWARD,
        )
        database_session.add(membership)
        database_session.commit()

        with override_user(steward):
            response = client.patch(f"/teams/{team.id}", json={"name": "Beta"})

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json()["error"]["code"] == "INSUFFICIENT_ROLE"
