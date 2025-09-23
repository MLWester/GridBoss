from __future__ import annotations

from collections.abc import Generator
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import Settings, get_settings
from app.db import Base
from app.db.models import User
from app.db.session import get_session
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
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


class StubDiscordClient:
    def __init__(self) -> None:  # pragma: no cover - settings unused in stub
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
    for table in Base.metadata.sorted_tables:
        for column in table.c:
            default = getattr(column, "server_default", None)
            if default is not None and "gen_random_uuid" in str(default.arg):
                column.server_default = None
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def override_dependencies() -> Generator[None, None, None]:
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

    get_settings.cache_clear()
    import app.main as app_main

    app_main.settings = test_settings

    def get_test_settings() -> Settings:
        return test_settings

    def get_test_session() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[provide_discord_client] = lambda: StubDiscordClient()

    yield

    app.dependency_overrides.clear()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


class TestAuthFlow:
    def test_redirect_sets_cookies(self, client: TestClient) -> None:
        response = client.get("/auth/discord/start", allow_redirects=False)
        assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
        assert "discord.com/api/oauth2/authorize" in response.headers["location"]
        assert "gb_pkce_verifier" in response.cookies
        assert "gb_oauth_state" in response.cookies

    def test_callback_creates_user_and_sets_tokens(self, client: TestClient) -> None:
        start_response = client.get("/auth/discord/start", allow_redirects=False)
        state_cookie = start_response.cookies.get("gb_oauth_state")
        verifier_cookie = start_response.cookies.get("gb_pkce_verifier")

        callback_response = client.get(
            "/auth/discord/callback",
            params={"code": "fake-code", "state": state_cookie},
            headers={
                "Cookie": f"gb_oauth_state={state_cookie}; gb_pkce_verifier={verifier_cookie}"
            },
            allow_redirects=False,
        )

        assert callback_response.status_code == HTTPStatus.FOUND
        assert "gb_refresh_token" in callback_response.cookies

        redirect_url = callback_response.headers["location"]
        parsed = urlparse(redirect_url)
        access_token = parse_qs(parsed.query).get("access_token", [None])[0]
        assert access_token is not None

        db: Session = TestingSessionLocal()
        try:
            assert db.query(User).count() == 1
        finally:
            db.close()

    def test_refresh_rotates_tokens(self, client: TestClient) -> None:
        start_response = client.get("/auth/discord/start", allow_redirects=False)
        state_cookie = start_response.cookies.get("gb_oauth_state")
        verifier_cookie = start_response.cookies.get("gb_pkce_verifier")
        callback_response = client.get(
            "/auth/discord/callback",
            params={"code": "fake-code", "state": state_cookie},
            headers={
                "Cookie": f"gb_oauth_state={state_cookie}; gb_pkce_verifier={verifier_cookie}"
            },
            allow_redirects=False,
        )
        refresh_cookie = callback_response.cookies.get("gb_refresh_token")

        client.cookies.set("gb_refresh_token", refresh_cookie)
        refresh_response = client.post("/auth/refresh")
        assert refresh_response.status_code == HTTPStatus.OK, refresh_response.json()
        body = refresh_response.json()
        assert "access_token" in body

    def test_me_requires_auth(self, client: TestClient) -> None:
        unauth = client.get("/auth/me")
        assert unauth.status_code == HTTPStatus.UNAUTHORIZED

        start_response = client.get("/auth/discord/start", allow_redirects=False)
        state_cookie = start_response.cookies.get("gb_oauth_state")
        verifier_cookie = start_response.cookies.get("gb_pkce_verifier")
        callback_response = client.get(
            "/auth/discord/callback",
            params={"code": "fake-code", "state": state_cookie},
            headers={
                "Cookie": f"gb_oauth_state={state_cookie}; gb_pkce_verifier={verifier_cookie}"
            },
            allow_redirects=False,
        )

        refresh_cookie = callback_response.cookies.get("gb_refresh_token")
        # rotate to ensure cookies valid for me request
        client.cookies.set("gb_refresh_token", refresh_cookie)
        refresh_response = client.post("/auth/refresh")
        assert refresh_response.status_code == HTTPStatus.OK, refresh_response.json()
        new_access_token = refresh_response.json()["access_token"]

        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response.status_code == HTTPStatus.OK, me_response.json()
        payload = me_response.json()
        assert payload["user"]["discord_id"] == "1234567890"
        assert payload["memberships"] == []

    def test_logout_clears_cookie(self, client: TestClient) -> None:
        client.cookies.set("gb_refresh_token", "dummy")
        response = client.post("/auth/logout")
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert "gb_refresh_token=" in response.headers.get("set-cookie", "")
