from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

import importlib
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "api"
for candidate in (ROOT, API_ROOT):
    if str(candidate) not in sys.path:
        sys.path.append(str(candidate))

if "dramatiq" not in sys.modules:
    class _ActorStub:
        def __init__(self, fn) -> None:
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

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.db.models import DiscordIntegration, League
import app.db.session as db_session
from bot.config import BotConfig
from bot.service import GridBossBot, InteractionContext


SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

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


def configure_session() -> None:
    db_session._engine = engine  # type: ignore[attr-defined]
    db_session.SessionLocal = TestingSessionLocal  # type: ignore[attr-defined]


def create_league(session: Session, *, plan: str = "PRO") -> League:
    league = League(name="League", slug=f"league-{uuid4().hex[:8]}", plan=plan)
    session.add(league)
    session.commit()
    session.refresh(league)
    return league


class DummyActor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def send(self, league_id: str, guild_id: str, channel_id: str) -> None:
        self.calls.append((league_id, guild_id, channel_id))


def setup_module() -> None:  # noqa: D401
    """Configure shared session for the module."""
    configure_session()


class TestGridBossBot:
    def setup_method(self) -> None:
        reset_database()
        import worker.jobs.discord as discord_jobs_module
        import bot.service as bot_service

        importlib.reload(discord_jobs_module)
        bot_service.discord_jobs = discord_jobs_module  # type: ignore[assignment]

        self.spied_actor = DummyActor()
        bot_service.discord_jobs.send_test_message = self.spied_actor  # type: ignore[assignment]

    def test_link_requires_admin(self) -> None:
        bot = GridBossBot(BotConfig(token="", app_url="http://local"))
        context = InteractionContext(guild_id="1", channel_id="10", user_id="100", is_admin=False)

        response = bot.process_command("link", context)

        assert "Manage Server" in response.content
        assert response.ephemeral is True

    def test_link_returns_signed_url(self) -> None:
        bot = GridBossBot(BotConfig(token="", app_url="https://gridboss.app"))
        context = InteractionContext(guild_id="987", channel_id="10", user_id="42", is_admin=True)

        response = bot.process_command("link", context)

        assert "https://gridboss.app/settings/discord?guildId=987" in response.content
        assert response.ephemeral is True

    def test_test_command_enqueues_job(self) -> None:
        bot = GridBossBot(BotConfig(token="", app_url="http://local"))
        session = TestingSessionLocal()
        league = create_league(session)
        integration = DiscordIntegration(
            league_id=league.id,
            guild_id="guild",
            channel_id="channel",
            installed_by_user=None,
            is_active=True,
        )
        session.add(integration)
        session.commit()

        context = InteractionContext(guild_id="guild", channel_id="channel", user_id="user", is_admin=True)
        response = bot.process_command("test", context)

        assert "Test message queued" in response.content
        assert self.spied_actor.calls == [(str(league.id), "guild", "channel")]

    def test_test_command_checks_integration_state(self) -> None:
        bot = GridBossBot(BotConfig(token="", app_url="http://local"))
        session = TestingSessionLocal()
        league = create_league(session)
        integration = DiscordIntegration(
            league_id=league.id,
            guild_id="guild",
            channel_id="channel",
            installed_by_user=None,
            is_active=False,
        )
        session.add(integration)
        session.commit()

        context = InteractionContext(guild_id="guild", channel_id="channel", user_id="user", is_admin=True)
        response = bot.process_command("test", context)

        assert "inactive" in response.content.lower()
        assert not self.spied_actor.calls
