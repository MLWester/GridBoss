from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.db.models import (
    Driver,
    Event,
    EventStatus,
    League,
    LeagueRole,
    Membership,
    PointsScheme,
    Result,
    Season,
    User,
)
from app.main import _prepare_sqlite_defaults, settings as app_settings
from scripts.seed_demo import (
    DEMO_LEAGUE_SLUG,
    DRIVER_NAMES,
    seed_demo,
)
from app.services.points import default_points_entries


@pytest.fixture()
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    db_path = tmp_path / "seed_demo.sqlite"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _prepare_sqlite_defaults(app_settings.app_env)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    yield SessionLocal

    engine.dispose()


def _run_seed(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        summary = seed_demo(session)
        session.commit()
        return summary


def _counts(session: Session, league: League) -> tuple[int, int, int]:
    driver_count = session.execute(
        select(func.count(Driver.id)).where(Driver.league_id == league.id)
    ).scalar_one()
    event_count = session.execute(
        select(func.count(Event.id)).where(Event.league_id == league.id)
    ).scalar_one()
    result_count = session.execute(
        select(func.count(Result.id)).join(Event).where(Event.league_id == league.id)
    ).scalar_one()
    return int(driver_count or 0), int(event_count or 0), int(result_count or 0)


def test_seed_demo_creates_expected_entities(session_factory: sessionmaker[Session]) -> None:
    summary = _run_seed(session_factory)

    assert summary.drivers == len(DRIVER_NAMES)
    assert summary.events == 3
    assert summary.results == len(DRIVER_NAMES)

    with session_factory() as session:
        league = session.execute(
            select(League).where(League.slug == DEMO_LEAGUE_SLUG)
        ).scalar_one()

        driver_count, event_count, result_count = _counts(session, league)
        assert driver_count == len(DRIVER_NAMES)
        assert event_count == 3
        assert result_count == len(DRIVER_NAMES)

        owner_membership = session.execute(
            select(Membership).where(Membership.league_id == league.id)
        ).scalar_one()
        assert owner_membership.role == LeagueRole.OWNER

        points_scheme = session.execute(
            select(PointsScheme).where(PointsScheme.league_id == league.id)
        ).scalar_one()
        assert len(points_scheme.rules) == len(default_points_entries())

        season = session.execute(
            select(Season).where(Season.league_id == league.id)
        ).scalar_one()
        assert season.is_active is True

        completed_events = session.execute(
            select(Event).where(
                Event.league_id == league.id, Event.status == EventStatus.COMPLETED.value
            )
        ).scalars().all()
        assert len(completed_events) == 1

        user_count = session.execute(select(func.count(User.id))).scalar_one()
        assert user_count == 1


def test_seed_demo_is_idempotent(session_factory: sessionmaker[Session]) -> None:
    first = _run_seed(session_factory)
    second = _run_seed(session_factory)

    assert first.to_dict() == second.to_dict()

    with session_factory() as session:
        league = session.execute(
            select(League).where(League.slug == DEMO_LEAGUE_SLUG)
        ).scalar_one()
        driver_count, event_count, result_count = _counts(session, league)

        assert driver_count == len(DRIVER_NAMES)
        assert event_count == 3
        assert result_count == len(DRIVER_NAMES)

        memberships = session.execute(
            select(func.count(Membership.id)).where(Membership.league_id == league.id)
        ).scalar_one()
        assert memberships == 1
