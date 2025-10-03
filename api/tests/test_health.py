from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.session import get_session
from app.main import app
from app.routes.health import clear_health_cache

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
        if default is not None and hasattr(default, "arg") and "gen_random_uuid" in str(default.arg):
            column.server_default = None

Base.metadata.create_all(bind=engine)


def reset_database() -> None:
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture()
def health_env(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[Settings, object], None, None]:
    reset_database()
    clear_health_cache()
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

    def get_test_session() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = lambda: settings

    from app.routes import health as health_routes

    redis_error = health_routes.redis.RedisError

    class StubRedis:
        should_fail = False

        @classmethod
        def from_url(cls, *_args, **_kwargs) -> "StubRedis":
            return cls()

        def ping(self) -> None:
            if type(self).should_fail:
                raise redis_error("forced failure")

        def close(self) -> None:
            pass

    StubRedis.should_fail = False
    monkeypatch.setattr(health_routes.redis, "Redis", StubRedis)

    try:
        yield settings, StubRedis
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        clear_health_cache()


@pytest.fixture()
def client(health_env: tuple[Settings, object]) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def test_healthz_includes_request_id(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "health-check"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "health-check"


def test_readyz_reports_ok(client: TestClient, health_env: tuple[Settings, object]) -> None:
    response = client.get("/readyz", headers={"X-Request-ID": "ready-ok"})

    payload = response.json()
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "ready-ok"
    assert payload["status"] == "ok"
    assert payload["checks"]["database"]["status"] == "ok"
    assert payload["checks"]["redis"]["status"] == "ok"
    assert payload["checks"]["migrations"]["status"] in {"ok", "unknown"}


def test_readyz_uses_cache(client: TestClient, health_env: tuple[Settings, object]) -> None:
    settings, stub = health_env
    settings.health_cache_seconds = 60

    first = client.get("/readyz").json()
    assert first["status"] == "ok"

    stub.should_fail = True
    second = client.get("/readyz").json()
    assert second == first


def test_readyz_degrades_on_redis_error(
    client: TestClient, health_env: tuple[Settings, object]
) -> None:
    _settings, stub = health_env
    stub.should_fail = True

    payload = client.get("/readyz").json()

    assert payload["status"] == "degraded"
    assert payload["checks"]["redis"]["status"] == "error"
