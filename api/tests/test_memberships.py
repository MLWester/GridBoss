from __future__ import annotations

from collections.abc import Generator
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import League, LeagueRole, Membership, User
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
        return {"access_token": "discord_token"}

    async def fetch_user(self, *, access_token: str) -> dict[str, str]:
        return {
            "id": "1234567890",
            "username": "TestDriver",
            "avatar": "avatar.png",
            "email": "driver@example.com",
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


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def preseed_db() -> Generator[tuple[Session, User, League], None, None]:
    session = TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    owner = User(discord_id="owner", discord_username="Owner")
    session.add(owner)
    session.commit()

    league = League(name="Test League", slug="test-league", owner_id=owner.id)
    session.add(league)
    session.commit()

    owner_membership = Membership(
        league_id=league.id,
        user_id=owner.id,
        role=LeagueRole.OWNER,
    )
    session.add(owner_membership)
    session.commit()

    try:
        yield session, owner, league
    finally:
        session.close()


class TestMembershipRoutes:
    def test_owner_can_invite_user(
        self,
        client: TestClient,
        preseed_db: tuple[Session, User, League],
    ) -> None:
        session, owner, league = preseed_db
        app.dependency_overrides[get_current_user] = lambda: owner

        new_user = User(discord_id="member", discord_username="Member")
        session.add(new_user)
        session.commit()

        response = client.post(
            f"/leagues/{league.id}/memberships",
            json={"user_id": str(new_user.id), "role": "ADMIN"},
        )
        assert response.status_code == HTTPStatus.CREATED, response.text
        data = response.json()
        assert data["user_id"] == str(new_user.id)
        assert data["role"] == "ADMIN"

    def test_steward_cannot_invite(
        self,
        client: TestClient,
        preseed_db: tuple[Session, User, League],
    ) -> None:
        session, owner, league = preseed_db
        steward = User(discord_id="steward", discord_username="Steward")
        session.add(steward)
        session.commit()
        session.add(Membership(league_id=league.id, user_id=steward.id, role=LeagueRole.STEWARD))
        session.commit()

        app.dependency_overrides[get_current_user] = lambda: steward

        response = client.post(
            f"/leagues/{league.id}/memberships",
            json={"user_id": str(uuid4()), "role": "DRIVER"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_admin_can_update_role(
        self,
        client: TestClient,
        preseed_db: tuple[Session, User, League],
    ) -> None:
        session, owner, league = preseed_db

        admin_user = User(discord_id="admin", discord_username="Admin")
        session.add(admin_user)
        session.commit()
        session.add(Membership(league_id=league.id, user_id=admin_user.id, role=LeagueRole.ADMIN))
        session.commit()

        target_user = User(discord_id="driver", discord_username="Driver")
        session.add(target_user)
        session.commit()
        membership = Membership(
            league_id=league.id,
            user_id=target_user.id,
            role=LeagueRole.DRIVER,
        )
        session.add(membership)
        session.commit()

        app.dependency_overrides[get_current_user] = lambda: admin_user

        response = client.patch(
            f"/leagues/{league.id}/memberships/{membership.id}",
            json={"role": "STEWARD"},
        )
        assert response.status_code == HTTPStatus.OK, response.text
        assert response.json()["role"] == "STEWARD"

    def test_cannot_demote_owner(
        self,
        client: TestClient,
        preseed_db: tuple[Session, User, League],
    ) -> None:
        session, owner, league = preseed_db
        admin_user = User(discord_id="admin", discord_username="Admin")
        session.add(admin_user)
        session.commit()
        session.add(Membership(league_id=league.id, user_id=admin_user.id, role=LeagueRole.ADMIN))
        session.commit()

        app.dependency_overrides[get_current_user] = lambda: admin_user

        owner_membership = session.execute(
            select(Membership).where(
                Membership.league_id == league.id,
                Membership.user_id == owner.id,
            )
        ).scalar_one()

        response = client.patch(
            f"/leagues/{league.id}/memberships/{owner_membership.id}",
            json={"role": "ADMIN"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_admin_can_remove_member(
        self,
        client: TestClient,
        preseed_db: tuple[Session, User, League],
    ) -> None:
        session, owner, league = preseed_db
        admin_user = User(discord_id="admin", discord_username="Admin")
        session.add(admin_user)
        session.commit()
        session.add(Membership(league_id=league.id, user_id=admin_user.id, role=LeagueRole.ADMIN))
        session.commit()

        target_user = User(discord_id="driver", discord_username="Driver")
        session.add(target_user)
        session.commit()
        membership = Membership(
            league_id=league.id,
            user_id=target_user.id,
            role=LeagueRole.DRIVER,
        )
        session.add(membership)
        session.commit()

        app.dependency_overrides[get_current_user] = lambda: admin_user

        response = client.delete(f"/leagues/{league.id}/memberships/{membership.id}")
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert (
            session.execute(
                select(Membership).where(Membership.id == membership.id)
            ).scalar_one_or_none()
            is None
        )
