from __future__ import annotations

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import api_error
from app.core.settings import Settings, get_settings
from app.db.models import (
    Driver,
    Event,
    EventStatus,
    LeagueRole,
    PointsScheme,
    Result,
    ResultStatus,
    User,
)
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.results import EventResultsRead, ResultEntryRead, ResultSubmission
from app.services.audit import record_audit_log
from app.services.idempotency import IdempotencyConfig, get_idempotency_service
from app.services.points import build_points_map, default_points_entries
from app.services.rbac import require_membership, require_role_at_least
from app.services.standings import StandingsCacheConfig, get_standings_cache

try:
    from worker.jobs import discord as discord_jobs
    from worker.jobs import standings
except Exception:  # pragma: no cover - worker optional during testing
    standings = None  # type: ignore
    discord_jobs = None  # type: ignore

logger = logging.getLogger("app.results")

router = APIRouter(tags=["results"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_SCOPE = "results"


class ResultsError(Exception):
    """Raised when results submission fails validation."""


def _load_event(session: Session, event_id: UUID) -> Event:
    event = session.execute(
        select(Event)
        .options(joinedload(Event.league), joinedload(Event.season))
        .where(Event.id == event_id)
    ).scalar_one_or_none()
    if event is None:
        raise ResultsError("EVENT_NOT_FOUND")
    return event


def _ensure_drivers(session: Session, league_id: UUID, driver_ids: set[UUID]) -> dict[UUID, Driver]:
    drivers = (
        session.execute(
            select(Driver).where(Driver.league_id == league_id, Driver.id.in_(driver_ids))
        )
        .scalars()
        .all()
    )
    if len(drivers) != len(driver_ids):
        missing = driver_ids - {driver.id for driver in drivers}
        raise ResultsError(f"MISSING_DRIVER:{next(iter(missing))}")
    return {driver.id: driver for driver in drivers}


def _load_points_scheme(session: Session, event: Event) -> dict[int, int]:
    season_id = event.season_id
    league_id = event.league_id

    scheme = (
        session.execute(
            select(PointsScheme)
            .options(joinedload(PointsScheme.rules))
            .where(
                PointsScheme.league_id == league_id,
                PointsScheme.season_id == season_id,
                PointsScheme.is_default.is_(True),
            )
        )
        .scalars()
        .first()
    )

    if scheme is None:
        scheme = (
            session.execute(
                select(PointsScheme)
                .options(joinedload(PointsScheme.rules))
                .where(
                    PointsScheme.league_id == league_id,
                    PointsScheme.season_id.is_(None),
                    PointsScheme.is_default.is_(True),
                )
            )
            .scalars()
            .first()
        )

    if scheme is None or not scheme.rules:
        return build_points_map(default_points_entries())

    entries = sorted(
        ((rule.position, rule.points) for rule in scheme.rules),
        key=lambda item: item[0],
    )
    return build_points_map(entries)


def _compute_total_points(
    base_points: int,
    bonus_points: int,
    penalty_points: int,
) -> int:
    total = base_points + bonus_points - penalty_points
    return total if total > 0 else 0


def _serialize_payload(entries: list[dict[str, str | int]]) -> str:
    return json.dumps(entries, sort_keys=True)


def _results_state(results: list[Result]) -> list[dict[str, object]]:
    return [
        {
            "driver_id": str(result.driver_id),
            "finish_position": result.finish_position,
            "started_position": result.started_position,
            "status": result.status,
            "bonus_points": result.bonus_points,
            "penalty_points": result.penalty_points,
            "total_points": result.total_points,
        }
        for result in results
    ]


def _build_response(event: Event, results: list[Result]) -> EventResultsRead:
    items = [
        ResultEntryRead(
            driver_id=result.driver_id,
            finish_position=result.finish_position,
            started_position=result.started_position,
            status=ResultStatus(result.status),
            bonus_points=result.bonus_points,
            penalty_points=result.penalty_points,
            total_points=result.total_points,
        )
        for result in sorted(results, key=lambda r: r.finish_position)
    ]
    return EventResultsRead(
        event_id=event.id,
        league_id=event.league_id,
        season_id=event.season_id,
        items=items,
    )


@router.post(
    "/events/{event_id}/results",
    response_model=EventResultsRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_results(
    event_id: UUID,
    payload: ResultSubmission,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", convert_underscores=False
    ),
) -> EventResultsRead:
    try:
        event = _load_event(session, event_id)
    except ResultsError as exc:
        if str(exc) == "EVENT_NOT_FOUND":

            raise api_error(
                status_code=status.HTTP_404_NOT_FOUND,
                code="EVENT_NOT_FOUND",
                message="Event not found",
            ) from exc
        raise

    membership = require_membership(session, league_id=event.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.STEWARD)

    previous_event_status = event.status

    entries = payload.entries
    driver_ids = {item.driver_id for item in entries}
    if len(driver_ids) != len(entries):

        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="DUPLICATE_DRIVER",
            message="Entries must be unique per driver",
        )

    finish_positions = {item.finish_position for item in entries}
    if len(finish_positions) != len(entries):

        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="DUPLICATE_POSITION",
            message="Entries must be unique per finish position",
        )

    try:
        drivers = _ensure_drivers(session, event.league_id, driver_ids)
    except ResultsError as exc:
        message = str(exc)
        if message.startswith("MISSING_DRIVER"):
            driver_identifier = message.split(":", 1)[1] if ":" in message else "unknown"
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="MISSING_DRIVER",
                message=f"Driver {driver_identifier} not found in league",
            )
        raise
    points_map = _load_points_scheme(session, event)

    existing_results = (
        session.execute(
            select(Result).where(Result.event_id == event.id).order_by(Result.finish_position)
        )
        .scalars()
        .all()
    )

    payload_hash = _serialize_payload(
        [
            {
                "driver_id": str(item.driver_id),
                "finish_position": item.finish_position,
                "bonus_points": item.bonus_points,
                "penalty_points": item.penalty_points,
            }
            for item in sorted(entries, key=lambda entry: entry.driver_id)
        ]
    )

    idem_service = get_idempotency_service(IdempotencyConfig(redis_url=settings.redis_url))

    idem_status: str | None = None
    if idempotency_key:
        idem_status = idem_service.claim(
            scope=f"{IDEMPOTENCY_SCOPE}:{event_id}", key=idempotency_key, payload_hash=payload_hash
        )
        if idem_status == "duplicate":
            return _build_response(event, existing_results)
        if idem_status == "conflict":

            raise api_error(
                status_code=status.HTTP_409_CONFLICT,
                code="IDEMPOTENCY_CONFLICT",
                message="Conflicting request for supplied Idempotency-Key",
            )

    try:
        session.execute(delete(Result).where(Result.event_id == event.id))

        results: list[Result] = []
        for entry in sorted(entries, key=lambda item: item.finish_position):
            driver = drivers[entry.driver_id]
            base_points = points_map.get(entry.finish_position, 0)
            total_points = _compute_total_points(
                base_points, entry.bonus_points, entry.penalty_points
            )
            result = Result(
                event_id=event.id,
                driver_id=driver.id,
                finish_position=entry.finish_position,
                started_position=entry.started_position,
                status=entry.status.value,
                bonus_points=entry.bonus_points,
                penalty_points=entry.penalty_points,
                total_points=total_points,
            )
            session.add(result)
            results.append(result)

        event.status = EventStatus.COMPLETED.value

        after_state = {"results": _results_state(results), "status": event.status}
        before_state = {
            "results": _results_state(existing_results),
            "status": previous_event_status,
        }
        if before_state != after_state:
            record_audit_log(
                session,
                actor_id=current_user.id,
                league_id=event.league_id,
                entity="event",
                entity_id=str(event.id),
                action="results_submitted",
                before=before_state,
                after=after_state,
            )

        session.commit()
    except Exception:
        session.rollback()
        if idempotency_key and idem_status == "claimed":  # allow retries
            idem_service.release(scope=f"{IDEMPOTENCY_SCOPE}:{event_id}", key=idempotency_key)
        raise

    session.refresh(event)
    cache = get_standings_cache(StandingsCacheConfig(redis_url=settings.redis_url))
    cache.invalidate(league_id=event.league_id, season_id=event.season_id)
    refreshed_results = (
        session.execute(
            select(Result).where(Result.event_id == event.id).order_by(Result.finish_position)
        )
        .scalars()
        .all()
    )

    _trigger_standings_jobs(event)

    return _build_response(event, refreshed_results)


def _trigger_standings_jobs(event: Event) -> None:
    if standings is None:
        logger.info("Results processed for event %s but worker jobs module unavailable.", event.id)
        return

    try:
        standings.recompute_standings.send(
            str(event.league_id),
            str(event.season_id) if event.season_id else None,
        )
    except Exception as exc:  # pragma: no cover - non-critical failure
        logger.warning("Failed to enqueue standings job: %s", exc)

    if discord_jobs is not None:
        try:
            discord_jobs.announce_results.send(
                str(event.league_id),
                str(event.id),
            )
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Failed to enqueue Discord announcement: %s", exc)


@router.get("/events/{event_id}/results", response_model=EventResultsRead)
async def read_results(
    event_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EventResultsRead:
    event = session.get(Event, event_id)
    if event is None:

        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message="Event not found",
        )

    require_membership(session, league_id=event.league_id, user_id=current_user.id)

    results = (
        session.execute(
            select(Result).where(Result.event_id == event.id).order_by(Result.finish_position)
        )
        .scalars()
        .all()
    )
    return _build_response(event, results)
