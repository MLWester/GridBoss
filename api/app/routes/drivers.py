from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import api_error
from app.core.observability import bind_league_id
from app.db.models import Driver, League, LeagueRole, Team, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.drivers import DriverBulkCreate, DriverRead, DriverUpdate
from app.services.rbac import require_membership, require_role_at_least

from app.services.plan import effective_driver_limit, get_billing_account_for_owner

router = APIRouter(tags=["drivers"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _get_league(league_id: UUID, session: SessionDep) -> League:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    bind_league_id(str(league.id))
    return league


def _driver_to_read(driver: Driver) -> DriverRead:
    return DriverRead(
        id=driver.id,
        league_id=driver.league_id,
        display_name=driver.display_name,
        user_id=driver.user_id,
        discord_id=driver.discord_id,
        team_id=driver.team_id,
        team_name=driver.team.name if driver.team else None,
    )


@router.get("/leagues/{league_id}/drivers", response_model=list[DriverRead])
async def list_drivers(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[DriverRead]:
    _get_league(league_id, session)
    require_membership(session, league_id=league_id, user_id=current_user.id)

    drivers = (
        session.execute(
            select(Driver)
            .options(joinedload(Driver.team))
            .where(Driver.league_id == league_id)
            .order_by(Driver.display_name)
        )
        .scalars()
        .all()
    )
    return [_driver_to_read(driver) for driver in drivers]


@router.post(
    "/leagues/{league_id}/drivers",
    response_model=list[DriverRead],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_drivers(
    league_id: UUID,
    payload: DriverBulkCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[DriverRead]:
    league = _get_league(league_id, session)
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    normalized_name_map: dict[str, str] = {}
    sanitized_items: list[tuple[str, UUID | None]] = []
    for item in payload.items:
        name = item.display_name.strip()
        if not name:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_NAME",
                message="Driver display name is required",
                field="display_name",
            )
        lowered = name.lower()
        if lowered in normalized_name_map:
            raise api_error(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_DRIVER",
                message="Duplicate driver names in request",
                field="display_name",
            )
        normalized_name_map[lowered] = name
        sanitized_items.append((name, item.team_id))

    team_ids = {team_id for (_, team_id) in sanitized_items if team_id is not None}
    if team_ids:
        teams = (
            session.execute(select(Team).where(Team.id.in_(team_ids), Team.league_id == league_id))
            .scalars()
            .all()
        )
        found_team_ids = {team.id for team in teams}
        missing = team_ids - found_team_ids
        if missing:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_TEAM",
                message="One or more teams do not belong to this league",
                field="team_id",
            )

    existing_names = {
        name.lower()
        for name in session.execute(
            select(Driver.display_name).where(Driver.league_id == league_id)
        ).scalars()
    }
    conflict = next((name for name in normalized_name_map if name in existing_names), None)
    if conflict is not None:
        raise api_error(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_DRIVER",
            message="Driver name already exists",
            field="display_name",
        )

    current_count = session.execute(
        select(func.count(Driver.id)).where(Driver.league_id == league_id)
    ).scalar_one()
    billing_account = get_billing_account_for_owner(session, league.owner_id)
    driver_limit = effective_driver_limit(league, billing_account)
    if current_count + len(sanitized_items) > driver_limit:
        raise api_error(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            code="PLAN_LIMIT",
            message="Driver limit reached for current plan",
        )

    drivers_to_create = [
        Driver(league_id=league_id, display_name=name, team_id=team_id)
        for name, team_id in sanitized_items
    ]
    session.add_all(drivers_to_create)
    session.commit()

    created_driver_ids = [driver.id for driver in drivers_to_create]
    created_drivers = (
        session.execute(
            select(Driver)
            .options(joinedload(Driver.team))
            .where(Driver.id.in_(created_driver_ids))
        )
        .scalars()
        .all()
    )
    created_lookup = {driver.id: driver for driver in created_drivers}
    return [_driver_to_read(created_lookup[driver_id]) for driver_id in created_driver_ids]


@router.patch("/drivers/{driver_id}", response_model=DriverRead)
async def update_driver(
    driver_id: UUID,
    payload: DriverUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DriverRead:
    driver = session.get(Driver, driver_id)
    if driver is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DRIVER_NOT_FOUND",
            message="Driver not found",
        )

    membership = require_membership(session, league_id=driver.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    update_data = payload.model_dump(exclude_unset=True)
    if "display_name" in update_data:
        raw_name = update_data["display_name"]
        new_name = raw_name.strip() if raw_name else ""
        if not new_name:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_NAME",
                message="Driver display name is required",
                field="display_name",
            )
        existing = session.execute(
            select(Driver)
            .where(
                Driver.league_id == driver.league_id,
                func.lower(Driver.display_name) == new_name.lower(),
                Driver.id != driver.id,
            )
        ).scalars().first()
        if existing:
            raise api_error(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_DRIVER",
                message="Driver name already exists",
                field="display_name",
            )
        driver.display_name = new_name

    if "team_id" in update_data:
        team_id = update_data["team_id"]
        if team_id is not None:
            team = session.get(Team, team_id)
            if team is None or team.league_id != driver.league_id:
                raise api_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="INVALID_TEAM",
                    message="Team does not belong to this league",
                    field="team_id",
                )
        driver.team_id = team_id

    session.commit()
    session.refresh(driver)
    return _driver_to_read(driver)


@router.delete("/drivers/{driver_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_driver(
    driver_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    driver = session.get(Driver, driver_id)
    if driver is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DRIVER_NOT_FOUND",
            message="Driver not found",
        )

    membership = require_membership(session, league_id=driver.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    session.delete(driver)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


