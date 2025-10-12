from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, LeagueRole, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.audit import AuditLogPage, AuditLogRead
from app.services.rbac import require_membership, require_role_at_least

router = APIRouter(tags=["audit"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("/audit/logs", response_model=AuditLogPage)
async def list_audit_logs(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AuditLogPage:
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    total = session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.league_id == league_id)
    ).scalar_one()

    offset = (page - 1) * page_size
    logs = (
        session.execute(
            select(AuditLog)
            .where(AuditLog.league_id == league_id)
            .order_by(AuditLog.timestamp.desc())
            .offset(offset)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    items = [AuditLogRead.from_orm_with_redaction(log) for log in logs]
    return AuditLogPage(items=items, page=page, page_size=page_size, total=total)


__all__ = ["router"]
