from __future__ import annotations

import importlib
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.session as db_session
from app.db import Base
from app.db.models import (
    AuditLog,
    DiscordIntegration,
    Driver,
    Event,
    EventStatus,
    League,
    Result,
    Season,
)

# Configure shared in-memory database for worker job tests.
engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
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


def configure_session() -> None:
    db_session._engine = engine  # type: ignore[attr-defined]
    db_session.SessionLocal = TestingSessionLocal  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def setup_db(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    configure_session()
    import worker.jobs.discord as discord_jobs_module
    import worker.services.discord as discord_service_module

    importlib.reload(discord_service_module)
    importlib.reload(discord_jobs_module)

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")

    yield

    reset_database()


class StubNotifier:
    def __init__(self, *, should_raise: Exception | None = None) -> None:
        self.messages: list[tuple[str, object]] = []
        self.should_raise = should_raise

    def send(self, channel_id: str, message: object) -> None:
        if self.should_raise:
            raise self.should_raise
        self.messages.append((channel_id, message))


def create_league(session: Session, *, plan: str = "PRO") -> League:
    league = League(name="League", slug=f"league-{uuid4().hex[:8]}", plan=plan)
    session.add(league)
    session.commit()
    session.refresh(league)
    return league


def create_event_with_results(session: Session, league: League) -> Event:
    season = Season(league_id=league.id, name="Season", is_active=True)
    event = Event(
        league_id=league.id,
        season=season,
        name="Race 1",
        track="Monza",
        start_time=datetime.now(UTC),
        status=EventStatus.COMPLETED.value,
    )
    driver = Driver(league_id=league.id, display_name="Driver A")
    session.add_all([season, event, driver])
    session.commit()
    session.refresh(event)
    result = Result(
        event_id=event.id,
        driver_id=driver.id,
        finish_position=1,
        started_position=1,
        status=EventStatus.COMPLETED.value,
        bonus_points=0,
        penalty_points=0,
        total_points=25,
    )
    session.add(result)
    session.commit()
    return event


def test_send_test_message_posts(monkeypatch: pytest.MonkeyPatch) -> None:
    import worker.jobs.discord as discord_jobs_module

    notifier = StubNotifier()
    monkeypatch.setattr(discord_jobs_module, "_get_notifier", lambda: notifier)

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

    discord_jobs_module.send_test_message.fn(str(league.id), "guild", "channel")

    assert notifier.messages and notifier.messages[0][0] == "channel"


def test_send_test_message_marks_inactive_on_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import worker.jobs.discord as discord_jobs_module
    from worker.services.discord import DiscordPermissionError

    notifier = StubNotifier(should_raise=DiscordPermissionError("forbidden"))
    monkeypatch.setattr(discord_jobs_module, "_get_notifier", lambda: notifier)

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

    with pytest.raises(DiscordPermissionError):
        discord_jobs_module.send_test_message.fn(str(league.id), "guild", "channel")

    session.close()
    check_session = TestingSessionLocal()
    refreshed = check_session.execute(
        select(DiscordIntegration).where(DiscordIntegration.id == integration.id)
    ).scalar_one()
    assert refreshed.is_active is False

    audit = check_session.execute(
        select(AuditLog).where(AuditLog.league_id == league.id)
    ).scalar_one()
    assert audit.action == "discord_deactivated"
    check_session.close()


def test_announce_results_sends_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    import worker.jobs.discord as discord_jobs_module

    notifier = StubNotifier()
    monkeypatch.setattr(discord_jobs_module, "_get_notifier", lambda: notifier)

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

    event = create_event_with_results(session, league)

    discord_jobs_module.announce_results.fn(str(league.id), str(event.id))

    assert notifier.messages
    channel, message = notifier.messages[0]
    assert channel == "channel"
    assert message.embeds and message.embeds[0]["title"].endswith("Results")


def test_announce_results_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import worker.jobs.discord as discord_jobs_module
    from worker.services.discord import DiscordRateLimitError

    notifier = StubNotifier(should_raise=DiscordRateLimitError("retry"))
    monkeypatch.setattr(discord_jobs_module, "_get_notifier", lambda: notifier)

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

    event = create_event_with_results(session, league)

    with pytest.raises(DiscordRateLimitError):
        discord_jobs_module.announce_results.fn(str(league.id), str(event.id))

    refreshed = session.execute(
        select(DiscordIntegration).where(DiscordIntegration.id == integration.id)
    ).scalar_one()
    assert refreshed.is_active is True
