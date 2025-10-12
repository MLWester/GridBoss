from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.observability import bind_league_id
from app.core.settings import Settings, get_settings
from app.db.models import League, Season, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.standings import SeasonStandingsRead, StandingsItem
from app.services.rbac import require_membership
from app.services.standings import (
    StandingsCacheConfig,
    calculate_standings,
    get_standings_cache,
)

router = APIRouter(tags=["standings"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _get_league(session: Session, league_id: UUID) -> League:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    bind_league_id(str(league.id))
    return league


def _resolve_season(
    session: Session,
    *,
    league_id: UUID,
    season_id: UUID | None,
) -> UUID | None:
    if season_id is not None:
        season = session.get(Season, season_id)
        if season is None or season.league_id != league_id:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_SEASON",
                message="Season does not belong to this league",
                field="season_id",
            )
        return season.id

    active = (
        session.execute(
            select(Season.id).where(Season.league_id == league_id, Season.is_active.is_(True))
        )
        .scalars()
        .first()
    )
    if active is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SEASON_NOT_FOUND",
            message="No active season configured for league",
        )
    return active


def _serialize_response(response: SeasonStandingsRead) -> dict[str, Any]:
    return {
        "league_id": str(response.league_id),
        "season_id": str(response.season_id) if response.season_id is not None else None,
        "items": [
            {
                "driver_id": str(item.driver_id),
                "display_name": item.display_name,
                "points": item.points,
                "wins": item.wins,
                "best_finish": item.best_finish,
            }
            for item in response.items
        ],
    }


def _deserialize_payload(payload: dict[str, Any]) -> SeasonStandingsRead:
    season_value = payload.get("season_id")
    return SeasonStandingsRead(
        league_id=UUID(payload["league_id"]),
        season_id=UUID(season_value) if season_value else None,
        items=[
            StandingsItem(
                driver_id=UUID(item["driver_id"]),
                display_name=item["display_name"],
                points=int(item["points"]),
                wins=int(item["wins"]),
                best_finish=int(item["best_finish"]) if item["best_finish"] is not None else None,
            )
            for item in payload.get("items", [])
        ],
    )


@router.get("/leagues/{league_id}/standings", response_model=SeasonStandingsRead)
async def read_standings(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    season_id: UUID | None = Query(default=None, alias="seasonId"),
) -> SeasonStandingsRead:
    _get_league(session, league_id)
    require_membership(session, league_id=league_id, user_id=current_user.id)

    resolved_season_id = _resolve_season(
        session,
        league_id=league_id,
        season_id=season_id,
    )

    cache = get_standings_cache(StandingsCacheConfig(redis_url=settings.redis_url))
    cached_payload = cache.get(league_id=league_id, season_id=resolved_season_id)
    if cached_payload is not None:
        return _deserialize_payload(cached_payload)

    raw_items = calculate_standings(
        session,
        league_id=league_id,
        season_id=resolved_season_id,
    )
    response = SeasonStandingsRead(
        league_id=league_id,
        season_id=resolved_season_id,
        items=[StandingsItem(**item) for item in raw_items],
    )
    cache.set(
        league_id=league_id,
        season_id=resolved_season_id,
        payload=_serialize_response(response),
    )
    return response
