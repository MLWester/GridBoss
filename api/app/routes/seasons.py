from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.models import League, LeagueRole, Season, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.seasons import SeasonCreate, SeasonRead, SeasonUpdate
from app.services.rbac import require_membership, require_role_at_least

router = APIRouter(tags=["seasons"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _get_league(session: Session, league_id: UUID) -> League:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    return league


def _season_to_read(season: Season) -> SeasonRead:
    return SeasonRead(
        id=season.id,
        league_id=season.league_id,
        name=season.name,
        is_active=season.is_active,
    )


@router.get("/leagues/{league_id}/seasons", response_model=list[SeasonRead])
async def list_seasons(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[SeasonRead]:
    _get_league(session, league_id)
    require_membership(session, league_id=league_id, user_id=current_user.id)

    seasons = (
        session.execute(
            select(Season).where(Season.league_id == league_id).order_by(Season.name)
        )
        .scalars()
        .all()
    )
    return [_season_to_read(season) for season in seasons]


@router.post(
    "/leagues/{league_id}/seasons",
    response_model=SeasonRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_season(
    league_id: UUID,
    payload: SeasonCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> SeasonRead:
    _get_league(session, league_id)
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    name = payload.name.strip()
    if not name:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_NAME",
            message="Season name is required",
            field="name",
        )

    desired_active = bool(payload.is_active)

    season = Season(league_id=league_id, name=name, is_active=desired_active)

    if desired_active:
        session.execute(
            update(Season)
            .where(Season.league_id == league_id, Season.is_active.is_(True))
            .values(is_active=False)
        )
    else:
        active_count = session.execute(
            select(func.count(Season.id)).where(
                Season.league_id == league_id, Season.is_active.is_(True)
            )
        ).scalar_one()
        if active_count == 0:
            season.is_active = True

    session.add(season)
    session.commit()
    session.refresh(season)
    return _season_to_read(season)


@router.patch("/seasons/{season_id}", response_model=SeasonRead)
async def update_season(
    season_id: UUID,
    payload: SeasonUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> SeasonRead:
    season = session.get(Season, season_id)
    if season is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SEASON_NOT_FOUND",
            message="Season not found",
        )

    membership = require_membership(session, league_id=season.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        new_name = update_data["name"].strip()
        if not new_name:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_NAME",
                message="Season name is required",
                field="name",
            )
        season.name = new_name

    if "is_active" in update_data and update_data["is_active"] is not None:
        desired_active = bool(update_data["is_active"])
        if desired_active:
            session.execute(
                update(Season)
                .where(Season.league_id == season.league_id, Season.is_active.is_(True), Season.id != season.id)
                .values(is_active=False)
            )
            season.is_active = True
        else:
            other_active = session.execute(
                select(func.count(Season.id)).where(
                    Season.league_id == season.league_id,
                    Season.is_active.is_(True),
                    Season.id != season.id,
                )
            ).scalar_one()
            if other_active == 0:
                raise api_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="LAST_ACTIVE_SEASON",
                    message="At least one season must remain active",
                )
            season.is_active = False

    session.commit()
    session.refresh(season)
    return _season_to_read(season)
