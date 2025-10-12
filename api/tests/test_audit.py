from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import AuditLog, League, LeagueRole, Membership, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.services.audit import record_audit_log

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

for table in Base.metadata.sorted_tables:
    for column in table.c:
        default = getattr(column, "server_default", None)
        if (
            default is not None
            and hasattr(default, "arg")
            and "gen_random_uuid" in str(default.arg)
        ):
            column.server_default = None

Base.metadata.create_all(bind=engine)


def reset_database() -> None:
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture(autouse=True)
def override_dependencies() -> None:
    reset_database()
    get_settings.cache_clear()
    settings = Settings(
        APP_ENV="test",
        APP_URL="http://localhost:5173",
        API_URL="http://localhost:8000",
        DISCORD_CLIENT_ID="client",
        DISCORD_CLIENT_SECRET="secret",
        DISCORD_REDIRECT_URI="http://localhost:8000/auth/discord/callback",
        JWT_SECRET="secret",
        JWT_ACCESS_TTL_MIN=15,
        JWT_REFRESH_TTL_DAYS=14,
        CORS_ORIGINS="http://localhost:5173",
        REDIS_URL="redis://localhost:6379/0",
    )

    def get_test_session() -> Session:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session] = get_test_session

    yield

    app.dependency_overrides.clear()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def session() -> Session:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_user(session: Session) -> User:
    user = User(
        discord_id=str(uuid4()),
        discord_username="user",
        email=f"{uuid4().hex}@example.com",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_league(session: Session, owner: User) -> League:
    league = League(name="League", slug=f"league-{uuid4().hex[:8]}", owner_id=owner.id)
    session.add(league)
    session.commit()
    session.refresh(league)
    membership = Membership(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER)
    session.add(membership)
    session.commit()
    return league


def add_member(session: Session, *, league: League, user: User, role: LeagueRole) -> None:
    membership = Membership(league_id=league.id, user_id=user.id, role=role)
    session.add(membership)
    session.commit()


def test_record_audit_log_serializes_state(session: Session) -> None:
    user = create_user(session)
    league = create_league(session, owner=user)
    timestamp = datetime.now(UTC)
    identifier = uuid4()

    record_audit_log(
        session,
        actor_id=user.id,
        league_id=league.id,
        entity="test",
        entity_id="123",
        action="update",
        before={"time": timestamp, "identifier": identifier},
        after={"state": "updated"},
    )
    session.commit()

    log = session.execute(select(AuditLog)).scalar_one()
    assert log.before_state["time"] == timestamp.isoformat()
    assert log.before_state["identifier"] == str(identifier)


def test_list_audit_logs_redacts_sensitive_fields(client: TestClient, session: Session) -> None:
    admin = create_user(session)
    league = create_league(session, owner=admin)

    record_audit_log(
        session,
        actor_id=admin.id,
        league_id=league.id,
        entity="example",
        entity_id="1",
        action="update",
        before={"secret": "value", "nested": {"token": "abc", "keep": "ok"}},
        after={"status": "ok"},
    )
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        response = client.get(f"/audit/logs?league_id={league.id}&page=1&page_size=10")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    log = payload["items"][0]
    assert log["before_state"]["secret"] == "[REDACTED]"
    assert log["before_state"]["nested"]["token"] == "[REDACTED]"
    assert log["before_state"]["nested"]["keep"] == "ok"


def test_list_audit_logs_requires_admin_role(client: TestClient, session: Session) -> None:
    owner = create_user(session)
    league = create_league(session, owner=owner)
    steward = create_user(session)
    add_member(session, league=league, user=steward, role=LeagueRole.STEWARD)

    record_audit_log(
        session,
        actor_id=owner.id,
        league_id=league.id,
        entity="example",
        entity_id="1",
        action="update",
        before={"status": "before"},
        after={"status": "after"},
    )
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: steward
    try:
        response = client.get(f"/audit/logs?league_id={league.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == status.HTTP_403_FORBIDDEN
