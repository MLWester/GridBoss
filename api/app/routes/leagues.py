from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.observability import bind_league_id
from app.core.settings import Settings, get_settings
from app.db.models import League, LeagueRole, Membership, Season, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.leagues import LeagueCreate, LeagueRead, LeagueUpdate
from app.services.audit import record_audit_log
from app.services.plan import (
    PLAN_DRIVER_LIMITS,
    effective_plan,
    get_billing_account_for_owner,
    is_league_limit_reached,
    league_limit,
)

router = APIRouter(prefix="/leagues", tags=["leagues"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

RESTORE_WINDOW_DAYS = 7


def _ensure_slug_available(session: Session, slug: str) -> None:
    exists = session.execute(
        select(League).where(League.slug == slug, League.is_deleted.is_(False))
    ).scalar_one_or_none()
    if exists:
        raise api_error(
            status_code=status.HTTP_409_CONFLICT,
            code="SLUG_IN_USE",
            message="Slug already in use",
        )


def _league_to_read(league: League) -> LeagueRead:
    return LeagueRead.model_validate(league)


def _active_league_count(
    session: Session,
    *,
    owner_id: UUID,
    exclude_league_id: UUID | None = None,
) -> int:
    query = select(func.count(League.id)).where(
        League.owner_id == owner_id,
        League.is_deleted.is_(False),
    )
    if exclude_league_id is not None:
        query = query.where(League.id != exclude_league_id)
    return session.execute(query).scalar_one()


def _ensure_league_capacity(
    *,
    session: Session,
    owner_id: UUID,
    plan: str,
    actor_id: UUID | None,
    context: str,
    exclude_league_id: UUID | None = None,
) -> None:
    active_count = _active_league_count(
        session, owner_id=owner_id, exclude_league_id=exclude_league_id
    )
    if not is_league_limit_reached(plan, active_count):
        return
    limit = league_limit(plan)
    record_audit_log(
        session,
        actor_id=actor_id,
        league_id=None,
        entity="plan",
        entity_id=str(owner_id),
        action="plan_limit_enforced",
        before={"context": context, "plan": plan, "active_leagues": active_count, "limit": limit},
        after=None,
    )
    session.commit()
    allowed = "unlimited" if limit is None else f"{limit}"
    raise api_error(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        code="PLAN_LIMIT",
        message=f"Current plan allows {allowed} active league(s). Upgrade to add another.",
    )


def _apply_plan_defaults(league: League, plan: str) -> None:
    driver_limit = PLAN_DRIVER_LIMITS.get(plan, PLAN_DRIVER_LIMITS["FREE"])
    league.plan = plan
    league.driver_limit = driver_limit


@router.post("", response_model=LeagueRead, status_code=status.HTTP_201_CREATED)
async def create_league(
    payload: LeagueCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
) -> LeagueRead:
    _ensure_slug_available(session, payload.slug)

    billing_account = get_billing_account_for_owner(session, current_user.id)
    current_plan = effective_plan(None, billing_account)
    _ensure_league_capacity(
        session=session,
        owner_id=current_user.id,
        plan=current_plan,
        actor_id=current_user.id,
        context="create_league",
    )

    league = League(name=payload.name, slug=payload.slug, owner_id=current_user.id)
    _apply_plan_defaults(league, current_plan)
    season = Season(league=league, name=f"{payload.name} Season", is_active=True)
    membership = Membership(league=league, user_id=current_user.id, role=LeagueRole.OWNER)

    session.add_all([league, season, membership])
    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league.id,
        entity="league",
        entity_id=str(league.id),
        action="create",
        before=None,
        after={"name": league.name, "slug": league.slug, "plan": league.plan},
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise api_error(
            status_code=status.HTTP_409_CONFLICT,
            code="SLUG_IN_USE",
            message="Slug already in use",
        ) from exc

    session.refresh(league)
    return _league_to_read(league)


@router.get("", response_model=list[LeagueRead])
async def list_leagues(session: SessionDep, current_user: CurrentUserDep) -> list[LeagueRead]:
    memberships = (
        session.execute(
            select(League)
            .join(Membership, Membership.league_id == League.id)
            .where(Membership.user_id == current_user.id, League.is_deleted.is_(False))
        )
        .scalars()
        .all()
    )
    return [_league_to_read(league) for league in memberships]


@router.get("/{league_id}", response_model=LeagueRead)
async def get_league(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LeagueRead:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    bind_league_id(str(league.id))

    membership = session.execute(
        select(Membership).where(
            Membership.league_id == league_id, Membership.user_id == current_user.id
        )
    ).scalar_one_or_none()
    if membership is None:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="NOT_A_MEMBER",
            message="You are not a member of this league",
        )

    return _league_to_read(league)


@router.patch("/{league_id}", response_model=LeagueRead)
async def update_league(
    league_id: UUID,
    payload: LeagueUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LeagueRead:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    bind_league_id(str(league.id))

    if league.owner_id != current_user.id:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="INSUFFICIENT_ROLE",
            message="Only the owner may update the league",
        )

    before_state = {"name": league.name, "slug": league.slug}

    if payload.slug and payload.slug != league.slug:
        _ensure_slug_available(session, payload.slug)
        league.slug = payload.slug

    if payload.name:
        league.name = payload.name

    if before_state != {"name": league.name, "slug": league.slug}:
        record_audit_log(
            session,
            actor_id=current_user.id,
            league_id=league.id,
            entity="league",
            entity_id=str(league.id),
            action="update",
            before=before_state,
            after={"name": league.name, "slug": league.slug},
        )

    session.commit()
    session.refresh(league)
    return _league_to_read(league)


@router.delete("/{league_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_league(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    bind_league_id(str(league.id))

    if league.owner_id != current_user.id:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="INSUFFICIENT_ROLE",
            message="Only the owner may delete the league",
        )

    before_state = {"name": league.name, "slug": league.slug}
    league.is_deleted = True
    league.deleted_at = datetime.now(timezone.utc)  # noqa: UP017
    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league.id,
        entity="league",
        entity_id=str(league.id),
        action="delete",
        before=before_state,
        after={"is_deleted": league.is_deleted, "deleted_at": league.deleted_at},
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{league_id}/restore", response_model=LeagueRead)
async def restore_league(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LeagueRead:
    league = session.get(League, league_id)
    if league is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    if not league.is_deleted:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="LEAGUE_ACTIVE",
            message="League is already active",
        )
    if league.owner_id != current_user.id:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="INSUFFICIENT_ROLE",
            message="Only the owner may restore the league",
        )

    deleted_at = league.deleted_at
    if deleted_at is None:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="LEAGUE_UNAVAILABLE",
            message="League cannot be restored",
        )
    if deleted_at.tzinfo is None:
        deleted_at = deleted_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)  # noqa: UP017
    if deleted_at + timedelta(days=RESTORE_WINDOW_DAYS) < now:
        raise api_error(
            status_code=status.HTTP_410_GONE,
            code="RESTORE_WINDOW_EXPIRED",
            message="Restore window has expired for this league",
        )

    billing_account = get_billing_account_for_owner(session, current_user.id)
    current_plan = effective_plan(league.plan, billing_account)
    _ensure_league_capacity(
        session=session,
        owner_id=current_user.id,
        plan=current_plan,
        actor_id=current_user.id,
        context="restore_league",
        exclude_league_id=league.id,
    )

    before_state = {
        "is_deleted": league.is_deleted,
        "deleted_at": league.deleted_at,
        "plan": league.plan,
        "driver_limit": league.driver_limit,
    }
    league.is_deleted = False
    league.deleted_at = None
    _apply_plan_defaults(league, current_plan)

    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league.id,
        entity="league",
        entity_id=str(league.id),
        action="restore",
        before=before_state,
        after={
            "is_deleted": league.is_deleted,
            "deleted_at": league.deleted_at,
            "plan": league.plan,
            "driver_limit": league.driver_limit,
        },
    )
    session.commit()
    session.refresh(league)
    bind_league_id(str(league.id))
    return _league_to_read(league)
