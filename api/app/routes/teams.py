from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.observability import bind_league_id
from app.db.models import Driver, League, LeagueRole, Team, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.teams import TeamCreate, TeamRead, TeamUpdate
from app.services.rbac import require_membership, require_role_at_least

router = APIRouter(tags=["teams"])

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
    bind_league_id(str(league.id))
    return league


def _team_to_read(team: Team, driver_count: int) -> TeamRead:
    return TeamRead(
        id=team.id,
        league_id=team.league_id,
        name=team.name,
        driver_count=driver_count,
    )


@router.get("/leagues/{league_id}/teams", response_model=list[TeamRead])
async def list_teams(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[TeamRead]:
    _get_league(session, league_id)
    require_membership(session, league_id=league_id, user_id=current_user.id)

    rows = session.execute(
        select(Team, func.count(Driver.id))
        .outerjoin(Driver, Driver.team_id == Team.id)
        .where(Team.league_id == league_id)
        .group_by(Team.id)
        .order_by(Team.name)
    ).all()
    return [_team_to_read(team, driver_count) for team, driver_count in rows]


@router.post(
    "/leagues/{league_id}/teams",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_team(
    league_id: UUID,
    payload: TeamCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TeamRead:
    _get_league(session, league_id)
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    name = payload.name.strip()
    if not name:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_NAME",
            message="Team name is required",
            field="name",
        )

    existing = (
        session.execute(
            select(Team).where(
                Team.league_id == league_id,
                func.lower(Team.name) == name.lower(),
            )
        )
        .scalars()
        .first()
    )
    if existing:
        raise api_error(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_TEAM",
            message="Team name already exists",
            field="name",
        )

    team = Team(league_id=league_id, name=name)
    session.add(team)
    session.commit()
    session.refresh(team)
    return _team_to_read(team, driver_count=0)


@router.patch("/teams/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TeamRead:
    team = session.get(Team, team_id)
    if team is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TEAM_NOT_FOUND",
            message="Team not found",
        )

    membership = require_membership(session, league_id=team.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        raw_name = update_data["name"]
        new_name = raw_name.strip() if raw_name else ""
        if not new_name:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_NAME",
                message="Team name is required",
                field="name",
            )
        existing = (
            session.execute(
                select(Team).where(
                    Team.league_id == team.league_id,
                    func.lower(Team.name) == new_name.lower(),
                    Team.id != team.id,
                )
            )
            .scalars()
            .first()
        )
        if existing:
            raise api_error(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_TEAM",
                message="Team name already exists",
                field="name",
            )
        team.name = new_name

    session.commit()
    session.refresh(team)

    driver_count = session.execute(
        select(func.count(Driver.id)).where(Driver.team_id == team.id)
    ).scalar_one()
    return _team_to_read(team, driver_count)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_team(
    team_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    team = session.get(Team, team_id)
    if team is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TEAM_NOT_FOUND",
            message="Team not found",
        )

    membership = require_membership(session, league_id=team.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    drivers = (
        session.execute(
            select(Driver).where(Driver.league_id == team.league_id, Driver.team_id == team.id)
        )
        .scalars()
        .all()
    )
    for driver in drivers:
        driver.team_id = None

    session.delete(team)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
