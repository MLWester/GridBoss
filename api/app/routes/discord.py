from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.observability import bind_league_id
from app.core.settings import Settings, get_settings
from app.db.models import DiscordIntegration, League, LeagueRole, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.dependencies.plan import requires_plan
from app.schemas.discord import DiscordIntegrationRead, DiscordLinkRequest
from app.services.audit import record_audit_log
from app.services.rbac import require_membership, require_role_at_least

try:
    from worker.jobs import discord as discord_jobs
except Exception:  # pragma: no cover - worker optional during testing
    discord_jobs = None  # type: ignore

logger = logging.getLogger("app.discord")

router = APIRouter(tags=["discord"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


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


def _integration_to_read(integration: DiscordIntegration) -> DiscordIntegrationRead:
    return DiscordIntegrationRead.model_validate(integration)


def _state_from_integration(integration: DiscordIntegration | None) -> dict[str, Any] | None:
    if integration is None:
        return None
    return {
        "guild_id": integration.guild_id,
        "channel_id": integration.channel_id,
        "installed_by_user": str(integration.installed_by_user) if integration.installed_by_user else None,
        "is_active": integration.is_active,
    }


@router.post(
    "/leagues/{league_id}/discord/link",
    response_model=DiscordIntegrationRead,
    status_code=status.HTTP_201_CREATED,
)
@requires_plan("PRO", message="Discord integration is available on the Pro plan")
async def link_discord_integration(
    league_id: UUID,
    payload: DiscordLinkRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> DiscordIntegrationRead:
    league = _get_league(league_id, session)
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    existing = (
        session.execute(
            select(DiscordIntegration).where(DiscordIntegration.league_id == league_id)
        )
        .scalars()
        .first()
    )

    before_state = _state_from_integration(existing)
    if existing is None:
        integration = DiscordIntegration(league_id=league_id)
    else:
        integration = existing

    integration.guild_id = payload.guild_id.strip()
    integration.channel_id = payload.channel_id.strip()
    integration.installed_by_user = current_user.id
    integration.is_active = True
    session.add(integration)
    session.flush()

    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league_id,
        entity="discord_integration",
        entity_id=str(integration.id),
        action="link",
        before=before_state,
        after=_state_from_integration(integration),
    )
    session.commit()
    session.refresh(integration)
    return _integration_to_read(integration)





@router.post(
    "/leagues/{league_id}/discord/test",
    status_code=status.HTTP_202_ACCEPTED,
)
@requires_plan("PRO", message="Discord integration is available on the Pro plan")
async def trigger_discord_test(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict[str, str]:
    league = _get_league(league_id, session)
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    integration = (
        session.execute(
            select(DiscordIntegration).where(DiscordIntegration.league_id == league_id)
        )
        .scalars()
        .first()
    )
    if integration is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DISCORD_NOT_LINKED",
            message="Discord integration not configured",
        )
    if not integration.is_active:
        raise api_error(
            status_code=status.HTTP_409_CONFLICT,
            code="INTEGRATION_INACTIVE",
            message="Discord integration is inactive",
        )
    if not integration.channel_id:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CHANNEL_NOT_SET",
            message="Discord channel is not configured",
        )

    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league_id,
        entity="discord_integration",
        entity_id=str(integration.id),
        action="test",
        before=_state_from_integration(integration),
        after=_state_from_integration(integration),
    )
    session.commit()

    if discord_jobs is None:
        logger.info(
            "Discord test requested for league %s but worker jobs are unavailable", league_id
        )
        return {"status": "queued"}

    try:
        discord_jobs.send_test_message.send(
            str(league_id),
            integration.guild_id,
            integration.channel_id,
        )
    except Exception as exc:  # pragma: no cover - job enqueue failures
        logger.warning("Failed to enqueue Discord test message: %s", exc)
        raise api_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DISCORD_QUEUE_UNAVAILABLE",
            message="Unable to enqueue Discord test message",
        ) from exc

    return {"status": "queued"}


