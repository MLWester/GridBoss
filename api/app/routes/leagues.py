from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.db.models import League, LeagueRole, Membership, Season, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.services.audit import record_audit_log
from app.schemas.leagues import LeagueCreate, LeagueRead, LeagueUpdate

router = APIRouter(prefix="/leagues", tags=["leagues"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _ensure_slug_available(session: Session, slug: str) -> None:
    exists = session.execute(
        select(League).where(League.slug == slug, League.is_deleted.is_(False))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")


def _league_to_read(league: League) -> LeagueRead:
    return LeagueRead.model_validate(league)


@router.post("", response_model=LeagueRead, status_code=status.HTTP_201_CREATED)
async def create_league(
    payload: LeagueCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
) -> LeagueRead:
    _ensure_slug_available(session, payload.slug)

    league = League(name=payload.name, slug=payload.slug, owner_id=current_user.id)
    season = Season(league=league, name=f"{payload.name} Season", is_active=True)
    membership = Membership(league=league, user_id=current_user.id, role=LeagueRole.OWNER)

    session.add_all([league, season, membership])
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slug already in use"
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")

    membership = session.execute(
        select(Membership).where(
            Membership.league_id == league_id, Membership.user_id == current_user.id
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a league member")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")

    if league.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner may update"
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")

    if league.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner may delete"
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
