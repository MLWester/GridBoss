from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db import Base
from app.db.models import Driver, Event, League, LeagueRole, Membership, Result, Season, User
from scripts.seed_demo import DRIVER_NAMES, seed_demo

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# SQLite does not understand postgres-specific defaults; drop them for tests
for table in Base.metadata.sorted_tables:
    for column in table.c:
        default = getattr(column, "server_default", None)
        if (
            default is not None
            and hasattr(default, "arg")
            and default.arg is not None
            and "gen_random_uuid" in str(default.arg)
        ):
            column.server_default = None

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    Base.metadata.create_all(bind=engine)


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_seed_demo_populates_expected_entities(session: Session) -> None:
    summary = seed_demo(session)
    session.commit()

    # Ensure summary values match persisted data
    league_id = UUID(summary.league_id)
    driver_count = session.execute(select(Driver).where(Driver.league_id == league_id)).scalars().all()
    event_count = session.execute(select(Event).where(Event.league_id == league_id)).scalars().all()
    result_count = session.execute(select(Result).join(Event).where(Event.league_id == league_id)).scalars().all()

    assert len(driver_count) == len(DRIVER_NAMES)
    assert len(event_count) == summary.events
    assert len(result_count) == summary.results

    owner: User = session.execute(select(User).where(User.id == UUID(summary.user_id))).scalar_one()
    league: League = session.execute(select(League).where(League.id == UUID(summary.league_id))).scalar_one()
    season: Season = session.execute(select(Season).where(Season.league_id == league.id)).scalar_one()
    membership: Membership = (
        session.execute(
            select(Membership).where(Membership.league_id == league.id, Membership.user_id == owner.id)
        ).scalar_one()
    )

    assert league.owner_id == owner.id
    assert membership.role == LeagueRole.OWNER
    assert season.is_active is True


def test_seed_demo_is_idempotent(session: Session) -> None:
    first = seed_demo(session)
    session.commit()

    second = seed_demo(session)
    session.commit()

    assert first.drivers == second.drivers == len(DRIVER_NAMES)
    assert first.events == second.events
    assert first.results == second.results

    # ensure rerun does not duplicate drivers/events/results
    league_id = UUID(first.league_id)
    driver_total = session.execute(select(Driver).where(Driver.league_id == league_id)).scalars().all()
    event_total = session.execute(select(Event).where(Event.league_id == league_id)).scalars().all()
    result_total = (
        session.execute(select(Result).join(Event).where(Event.league_id == UUID(first.league_id))).scalars().all()
    )

    assert len(driver_total) == len(DRIVER_NAMES)
    assert len(event_total) == first.events
    assert len(result_total) == first.results
