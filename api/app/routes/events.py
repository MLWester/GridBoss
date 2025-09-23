from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.models import Event, EventStatus, League, LeagueRole, Season, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.events import EventCreate, EventRead, EventUpdate
from app.services.rbac import require_membership, require_role_at_least

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore

router = APIRouter(tags=["events"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


STATUS_LOOKUP = {item.value: item for item in EventStatus}
SPECIAL_FILTERS = {"UPCOMING", "PAST"}


def _get_league(session: Session, league_id: UUID) -> League:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    return league


def _ensure_season(session: Session, *, league_id: UUID, season_id: UUID | None) -> UUID | None:
    if season_id is None:
        return None
    season = session.get(Season, season_id)
    if season is None or season.league_id != league_id:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_SEASON",
            message="Season does not belong to this league",
            field="season_id",
        )
    return season_id


def _parse_timezone(value: str | None) -> ZoneInfo | None:
    if value is None:
        return None
    try:
        return ZoneInfo(value)
    except Exception as exc:  # pragma: no cover
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_TIMEZONE",
            message="Invalid timezone identifier",
            field="tz",
        ) from exc


def _event_to_read(event: Event, tz: ZoneInfo | None = None) -> EventRead:
    start_time = event.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    else:
        start_time = start_time.astimezone(UTC)
    display_time = start_time if tz is None else start_time.astimezone(tz)
    return EventRead(
        id=event.id,
        league_id=event.league_id,
        season_id=event.season_id,
        name=event.name,
        track=event.track,
        start_time=display_time,
        laps=event.laps,
        distance_km=float(event.distance_km) if event.distance_km is not None else None,
        status=EventStatus(event.status),
    )
def _apply_status_filters(
    statement: Select[tuple[Event]],
    *,
    status_tokens: set[str],
) -> Select[tuple[Event]]:
    now = datetime.now(UTC)
    event_statuses: set[str] = set()
    include_upcoming = False
    include_past = False

    for token in status_tokens:
        upper = token.upper()
        if upper in SPECIAL_FILTERS:
            if upper == "UPCOMING":
                include_upcoming = True
            elif upper == "PAST":
                include_past = True
            continue
        if upper not in STATUS_LOOKUP:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_STATUS",
                message="Unsupported status filter",
                field="status",
            )
        event_statuses.add(upper)

    if event_statuses:
        statement = statement.where(Event.status.in_(event_statuses))

    if include_upcoming:
        statement = statement.where(
            Event.status == EventStatus.SCHEDULED.value,
            Event.start_time >= now,
        )
    if include_past:
        statement = statement.where(Event.status == EventStatus.COMPLETED.value)

    return statement


@router.get(
    "/leagues/{league_id}/events",
    response_model=list[EventRead],
)
async def list_events(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    tz: str | None = None,
) -> list[EventRead]:
    _get_league(session, league_id)
    require_membership(session, league_id=league_id, user_id=current_user.id)

    tzinfo = _parse_timezone(tz)
    status_tokens: set[str] = set()
    if status_filter:
        status_tokens = {token.strip() for token in status_filter.split(",") if token.strip()}

    statement: Select[tuple[Event]] = select(Event).where(Event.league_id == league_id)
    if status_tokens:
        statement = _apply_status_filters(statement, status_tokens=status_tokens)

    statement = statement.order_by(Event.start_time.asc())

    events = session.execute(statement).scalars().all()
    return [_event_to_read(event, tz=tzinfo) for event in events]


@router.post(
    "/leagues/{league_id}/events",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    league_id: UUID,
    payload: EventCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EventRead:
    _get_league(session, league_id)
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    start_time = payload.start_time
    if start_time.tzinfo is None:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_START_TIME",
            message="start_time must include timezone information",
            field="start_time",
        )
    start_time_utc = start_time.astimezone(UTC)

    season_id = _ensure_season(session, league_id=league_id, season_id=payload.season_id)

    event = Event(
        league_id=league_id,
        season_id=season_id,
        name=payload.name.strip(),
        track=payload.track.strip(),
        start_time=start_time_utc,
        laps=payload.laps,
        distance_km=payload.distance_km,
        status=EventStatus.SCHEDULED.value,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return _event_to_read(event)


@router.get("/events/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    tz: str | None = None,
) -> EventRead:
    event = session.get(Event, event_id)
    if event is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message="Event not found",
        )

    require_membership(session, league_id=event.league_id, user_id=current_user.id)
    tzinfo = _parse_timezone(tz)
    return _event_to_read(event, tz=tzinfo)


@router.patch("/events/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EventRead:
    event = session.get(Event, event_id)
    if event is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message="Event not found",
        )

    membership = require_membership(session, league_id=event.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    update_data = payload.model_dump(exclude_unset=True)

    is_completed = event.status == EventStatus.COMPLETED.value

    if "name" in update_data and update_data["name"] is not None:
        if is_completed:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="EVENT_COMPLETED",
                message="Completed events may not be edited",
            )
        new_name = update_data["name"].strip()
        if not new_name:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_NAME",
                message="Event name is required",
                field="name",
            )
        event.name = new_name

    if "track" in update_data and update_data["track"] is not None:
        if is_completed:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="EVENT_COMPLETED",
                message="Completed events may not be edited",
            )
        new_track = update_data["track"].strip()
        if not new_track:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_TRACK",
                message="Track name is required",
                field="track",
            )
        event.track = new_track

    if "start_time" in update_data and update_data["start_time"] is not None:
        if is_completed:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="EVENT_COMPLETED",
                message="Completed events may not be edited",
            )
        start_time = update_data["start_time"]
        if start_time.tzinfo is None:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_START_TIME",
                message="start_time must include timezone information",
                field="start_time",
            )
        event.start_time = start_time.astimezone(UTC)

    if "season_id" in update_data:
        season_id = _ensure_season(
            session, league_id=event.league_id, season_id=update_data["season_id"]
        )
        event.season_id = season_id

    if "laps" in update_data:
        event.laps = update_data["laps"]

    if "distance_km" in update_data:
        event.distance_km = update_data["distance_km"]

    if "status" in update_data and update_data["status"] is not None:
        new_status = update_data["status"].value
        if event.status == EventStatus.COMPLETED.value and new_status != EventStatus.COMPLETED.value:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="EVENT_COMPLETED",
                message="Completed events cannot change status",
            )
        event.status = new_status

    session.commit()
    session.refresh(event)
    return _event_to_read(event)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_event(
    event_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    event = session.get(Event, event_id)
    if event is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message="Event not found",
        )

    membership = require_membership(session, league_id=event.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    if event.status == EventStatus.COMPLETED.value:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="EVENT_COMPLETED",
            message="Completed events cannot be canceled",
        )

    event.status = EventStatus.CANCELED.value
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)




