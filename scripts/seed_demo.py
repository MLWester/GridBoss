from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Iterable, List

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import (
    Driver,
    Event,
    EventStatus,
    League,
    LeagueRole,
    Membership,
    PointsRule,
    PointsScheme,
    Result,
    ResultStatus,
    Season,
    User,
)
from app.db.session import get_sessionmaker
from app.services.points import default_points_entries

LOGGER = logging.getLogger("seed_demo")

DEMO_USER_EMAIL = "demo@gridboss.app"
DEMO_USER_NAME = "Demo Owner"
DEMO_LEAGUE_NAME = "Demo GP"
DEMO_LEAGUE_SLUG = "demo-gp"
DEMO_SEASON_NAME = "2025 Championship"
POINTS_SCHEME_NAME = "Demo Points Scheme"
DRIVER_NAMES: List[str] = [
    "Alex Rivera",
    "Jamie Chen",
    "Morgan Patel",
    "Taylor Brooks",
    "Riley Nakamura",
    "Jordan Vasseur",
    "Casey Muller",
    "Sydney Alvarez",
    "Devon Clarke",
    "Hayden Rossi",
]


@dataclass
class SeedSummary:
    user_id: str
    league_id: str
    drivers: int
    events: int
    results: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "user_id": self.user_id,
            "league_id": self.league_id,
            "drivers": self.drivers,
            "events": self.events,
            "results": self.results,
        }


def _ensure_user(session: Session) -> User:
    user = session.execute(select(User).where(User.email == DEMO_USER_EMAIL)).scalar_one_or_none()
    if user is None:
        user = User(email=DEMO_USER_EMAIL, discord_username=DEMO_USER_NAME, is_active=True)
        session.add(user)
    else:
        user.discord_username = DEMO_USER_NAME
        user.is_active = True
    session.flush()
    return user


def _ensure_league(session: Session, owner: User) -> League:
    league = session.execute(select(League).where(League.slug == DEMO_LEAGUE_SLUG)).scalar_one_or_none()
    if league is None:
        league = League(name=DEMO_LEAGUE_NAME, slug=DEMO_LEAGUE_SLUG, plan="PRO", driver_limit=50)
        session.add(league)
    league.name = DEMO_LEAGUE_NAME
    league.plan = "PRO"
    league.driver_limit = max(league.driver_limit, len(DRIVER_NAMES))
    league.owner = owner
    session.flush()
    return league


def _ensure_membership(session: Session, league: League, owner: User) -> None:
    membership = session.execute(
        select(Membership).where(Membership.league_id == league.id, Membership.user_id == owner.id)
    ).scalar_one_or_none()
    if membership is None:
        membership = Membership(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER)
        session.add(membership)
    else:
        membership.role = LeagueRole.OWNER
    session.flush()


def _ensure_season(session: Session, league: League) -> Season:
    season = session.execute(
        select(Season).where(Season.league_id == league.id, Season.name == DEMO_SEASON_NAME)
    ).scalar_one_or_none()
    if season is None:
        season = Season(league_id=league.id, name=DEMO_SEASON_NAME, is_active=True)
        session.add(season)
    season.is_active = True
    session.flush()
    return season


def _ensure_points_scheme(session: Session, league: League, season: Season) -> PointsScheme:
    scheme = session.execute(
        select(PointsScheme).where(
            PointsScheme.league_id == league.id, PointsScheme.name == POINTS_SCHEME_NAME
        )
    ).scalar_one_or_none()
    created = False
    if scheme is None:
        scheme = PointsScheme(league_id=league.id, season_id=season.id, name=POINTS_SCHEME_NAME)
        session.add(scheme)
        created = True
    scheme.season_id = season.id
    scheme.is_default = True
    session.flush()

    entries = default_points_entries()
    scheme.rules.clear()
    for position, points in entries:
        scheme.rules.append(PointsRule(position=position, points=points))
    session.flush()
    if created:
        LOGGER.debug("Created points scheme %s", scheme.id)
    return scheme


def _ensure_drivers(session: Session, league: League) -> List[Driver]:
    drivers: List[Driver] = []
    for name in DRIVER_NAMES:
        driver = session.execute(
            select(Driver).where(Driver.league_id == league.id, Driver.display_name == name)
        ).scalar_one_or_none()
        if driver is None:
            driver = Driver(league_id=league.id, display_name=name)
            session.add(driver)
        else:
            driver.display_name = name
        drivers.append(driver)
    session.flush()
    return drivers


def _ensure_events(
    session: Session,
    league: League,
    season: Season,
    drivers: List[Driver],
    points_map: Dict[int, int],
) -> List[Event]:
    now = datetime.now(timezone.utc)
    event_definitions = [
        {
            "name": "Bahrain Grand Prix",
            "track": "Bahrain International Circuit",
            "start_time": now - timedelta(days=21),
            "status": EventStatus.COMPLETED.value,
            "laps": 57,
            "distance_km": Decimal("308.24"),
            "results": [
                {"position": idx + 1, "driver": drivers[idx]} for idx in range(len(drivers))
            ],
        },
        {
            "name": "Saudi Arabian Grand Prix",
            "track": "Jeddah Corniche Circuit",
            "start_time": now + timedelta(days=7),
            "status": EventStatus.SCHEDULED.value,
            "laps": 50,
            "distance_km": Decimal("308.45"),
        },
        {
            "name": "Australian Grand Prix",
            "track": "Albert Park Circuit",
            "start_time": now + timedelta(days=21),
            "status": EventStatus.SCHEDULED.value,
            "laps": 58,
            "distance_km": Decimal("307.57"),
        },
    ]

    events: List[Event] = []
    for definition in event_definitions:
        event = session.execute(
            select(Event).where(Event.league_id == league.id, Event.name == definition["name"])
        ).scalar_one_or_none()
        if event is None:
            event = Event(league_id=league.id, season_id=season.id, name=definition["name"], track="")
            session.add(event)
        event.track = definition["track"]
        event.season_id = season.id
        event.start_time = definition["start_time"]
        event.status = definition["status"]
        event.laps = definition["laps"]
        event.distance_km = definition["distance_km"]
        events.append(event)
        session.flush()

        results_def = definition.get("results")
        if results_def is not None:
            session.execute(delete(Result).where(Result.event_id == event.id))
            for item in results_def:
                driver: Driver = item["driver"]
                position = item["position"]
                base_points = points_map.get(position, 0)
                result = Result(
                    event_id=event.id,
                    driver_id=driver.id,
                    finish_position=position,
                    started_position=position,
                    status=ResultStatus.FINISHED.value,
                    bonus_points=0,
                    penalty_points=0,
                    total_points=base_points,
                )
                session.add(result)
    session.flush()
    return events


def seed_demo(session: Session) -> SeedSummary:
    """Populate the database with demo data. Run inside a transaction."""

    user = _ensure_user(session)
    league = _ensure_league(session, user)
    _ensure_membership(session, league, user)
    season = _ensure_season(session, league)
    scheme = _ensure_points_scheme(session, league, season)
    drivers = _ensure_drivers(session, league)
    points_map = {position: points for position, points in default_points_entries()}
    events = _ensure_events(session, league, season, drivers, points_map)

    driver_count = session.execute(
        select(func.count(Driver.id)).where(Driver.league_id == league.id)
    ).scalar_one()
    event_count = session.execute(
        select(func.count(Event.id)).where(Event.league_id == league.id)
    ).scalar_one()
    result_count = session.execute(
        select(func.count(Result.id)).join(Event).where(Event.league_id == league.id)
    ).scalar_one()

    summary = SeedSummary(
        user_id=str(user.id),
        league_id=str(league.id),
        drivers=int(driver_count or 0),
        events=int(event_count or 0),
        results=int(result_count or 0),
    )
    LOGGER.info(
        "Seeded demo league '%s' with %d drivers, %d events, %d results",
        league.name,
        summary.drivers,
        summary.events,
        summary.results,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo league data into the database.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the seeding logic but rollback instead of committing.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the summary as JSON to stdout.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    session_maker = get_sessionmaker()
    session = session_maker()
    try:
        summary = seed_demo(session)
        if args.dry_run:
            session.rollback()
        else:
            session.commit()
    finally:
        session.close()

    payload = summary.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Seeded demo league {payload['league_id']} with "
            f"{payload['drivers']} drivers, {payload['events']} events, {payload['results']} results"
        )


if __name__ == "__main__":
    main()
