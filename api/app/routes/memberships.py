from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.db.models import League, LeagueRole, Membership, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.memberships import MembershipCreate, MembershipRead, MembershipUpdate
from app.services.email import queue_transactional_email

router = APIRouter(prefix="/leagues/{league_id}/memberships", tags=["memberships"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

ROLE_PRIORITY = {
    LeagueRole.DRIVER: 1,
    LeagueRole.STEWARD: 2,
    LeagueRole.ADMIN: 3,
    LeagueRole.OWNER: 4,
}


def _require_membership(session: Session, league_id: UUID, user_id: UUID) -> Membership:
    membership = session.execute(
        select(Membership).where(Membership.league_id == league_id, Membership.user_id == user_id)
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a league member")
    return membership


def _require_role(membership: Membership, minimum: LeagueRole) -> None:
    if ROLE_PRIORITY[membership.role] < ROLE_PRIORITY[minimum]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _membership_to_read(membership: Membership) -> MembershipRead:
    return MembershipRead.model_validate(
        {
            "id": membership.id,
            "league_id": membership.league_id,
            "user_id": membership.user_id,
            "role": membership.role,
        }
    )


@router.get("", response_model=list[MembershipRead])
async def list_memberships(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[MembershipRead]:
    _require_membership(session, league_id, current_user.id)
    memberships = (
        session.execute(select(Membership).where(Membership.league_id == league_id)).scalars().all()
    )
    return [_membership_to_read(m) for m in memberships]


@router.post("", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
async def create_membership(
    league_id: UUID,
    payload: MembershipCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
) -> MembershipRead:
    actor_membership = _require_membership(session, league_id, current_user.id)
    _require_role(actor_membership, LeagueRole.ADMIN)

    if actor_membership.user_id == payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify own membership",
        )

    league = session.execute(select(League).where(League.id == league_id)).scalar_one_or_none()
    if league is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")

    target_user = session.get(User, payload.user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = session.execute(
        select(Membership).where(
            Membership.league_id == league_id,
            Membership.user_id == payload.user_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already a member")

    membership = Membership(league_id=league_id, user_id=payload.user_id, role=payload.role)
    session.add(membership)
    session.commit()
    session.refresh(membership)

    if target_user.email:
        inviter_name = current_user.discord_username or current_user.email or "League admin"
        queue_transactional_email(
            template_id="league_invite",
            recipient=target_user.email,
            context={
                "display_name": target_user.discord_username or "Driver",
                "inviter_name": inviter_name,
                "league_name": league.name,
                "league_url": f"{settings.app_url}/leagues/{league.slug}",
            },
            league_id=str(league.id),
            actor_id=str(current_user.id),
        )

    return _membership_to_read(membership)


@router.patch("/{membership_id}", response_model=MembershipRead)
async def update_membership(
    league_id: UUID,
    membership_id: UUID,
    payload: MembershipUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> MembershipRead:
    actor_membership = _require_membership(session, league_id, current_user.id)
    _require_role(actor_membership, LeagueRole.ADMIN)

    membership = session.get(Membership, membership_id)
    if membership is None or membership.league_id != league_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    league = session.get(League, league_id)
    if league is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")

    if (
        membership.role == LeagueRole.OWNER
        and membership.user_id == league.owner_id
        and payload.role != LeagueRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote the active owner",
        )

    membership.role = payload.role
    if payload.role == LeagueRole.OWNER:
        league.owner_id = membership.user_id
    session.commit()
    session.refresh(membership)
    return _membership_to_read(membership)


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_membership(
    league_id: UUID,
    membership_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    actor_membership = _require_membership(session, league_id, current_user.id)
    _require_role(actor_membership, LeagueRole.ADMIN)

    membership = session.get(Membership, membership_id)
    if membership is None or membership.league_id != league_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    league = session.get(League, league_id)
    if league is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")

    if membership.role == LeagueRole.OWNER and membership.user_id == league.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the owner",
        )

    session.delete(membership)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
