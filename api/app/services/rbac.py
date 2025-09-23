from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.models import LeagueRole, Membership

ROLE_PRIORITY = {
    LeagueRole.DRIVER: 1,
    LeagueRole.STEWARD: 2,
    LeagueRole.ADMIN: 3,
    LeagueRole.OWNER: 4,
}

def require_membership(session: Session, *, league_id: UUID, user_id: UUID) -> Membership:
    membership = session.execute(
        select(Membership).where(Membership.league_id == league_id, Membership.user_id == user_id)
    ).scalar_one_or_none()
    if membership is None:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="NOT_A_MEMBER",
            message="Not a member of this league",
        )
    return membership

def require_role_at_least(membership: Membership, *, minimum: LeagueRole) -> None:
    required_rank = ROLE_PRIORITY[minimum]
    actual_rank = ROLE_PRIORITY[membership.role]
    if actual_rank < required_rank:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="INSUFFICIENT_ROLE",
            message="Insufficient permissions for this action",
        )
