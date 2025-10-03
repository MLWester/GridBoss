from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DiscordIntegration
from app.services.audit import record_audit_log
from app.db.session import get_sessionmaker
from worker.jobs import discord as discord_jobs

from .config import BotConfig


@dataclass
class InteractionContext:
    guild_id: str
    channel_id: str
    user_id: str
    is_admin: bool


@dataclass
class CommandResponse:
    content: str
    ephemeral: bool = True



def _integration_state(integration: DiscordIntegration) -> dict[str, Any]:
    return {
        "guild_id": integration.guild_id,
        "channel_id": integration.channel_id,
        "is_active": integration.is_active,
    }


def _record_bot_failure(
    session: Session,
    integration: DiscordIntegration,
    *,
    reason: str,
    requested_by: str,
) -> None:
    state = _integration_state(integration)
    record_audit_log(
        session,
        actor_id=None,
        league_id=integration.league_id,
        entity="discord_integration",
        entity_id=str(integration.id),
        action="bot_command_denied",
        before=state,
        after={**state, "reason": reason, "requested_by": requested_by},
    )
    session.commit()


class GridBossBot:
    """Command-first Discord bot orchestration for GridBoss."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._session_factory = get_sessionmaker()
        self._commands: Dict[str, Callable[[InteractionContext], CommandResponse]] = {
            "link": self._handle_link,
            "test": self._handle_test,
        }

    @property
    def commands(self) -> dict[str, str]:
        return {
            "link": "Generate a secure link to connect this Discord server to GridBoss.",
            "test": "Verify the bot can post to the configured channel.",
        }

    def process_command(self, name: str, context: InteractionContext) -> CommandResponse:
        handler = self._commands.get(name)
        if handler is None:
            return CommandResponse(content="Unknown command.")
        return handler(context)

    def _handle_link(self, context: InteractionContext) -> CommandResponse:
        if not context.is_admin:
            return CommandResponse(
                content="You need the Manage Server permission to link this Discord server to GridBoss.",
                ephemeral=True,
            )

        link_url = f"{self.config.app_url}{self.config.link_path}?guildId={context.guild_id}"
        message = (
            "🔗 Use the secure link below to connect this server to GridBoss."
            " Only Owners/Admins in your league can complete the flow.\n\n"
            f"<{link_url}>"
        )
        return CommandResponse(content=message, ephemeral=True)

    def _handle_test(self, context: InteractionContext) -> CommandResponse:
        if not context.is_admin:
            return CommandResponse(
                content="You need the Manage Server permission to run a test.",
                ephemeral=True,
            )

        session: Session = self._session_factory()
        try:
            integration = (
                session.execute(
                    select(DiscordIntegration).where(DiscordIntegration.guild_id == context.guild_id)
                )
                .scalars()
                .first()
            )
            if integration is None:
                return CommandResponse(
                    content="This server has not been linked to a GridBoss league yet.", ephemeral=True
                )
            if not integration.is_active:
                _record_bot_failure(
                    session, integration, reason="integration_inactive", requested_by=context.user_id
                )
                return CommandResponse(
                    content="The Discord integration is currently inactive. An admin should relink it via GridBoss.",
                    ephemeral=True,
                )
            if not integration.channel_id:
                _record_bot_failure(
                    session, integration, reason="channel_missing", requested_by=context.user_id
                )
                return CommandResponse(
                    content="No announcement channel is configured. Update the integration in GridBoss first.",
                    ephemeral=True,
                )

            discord_jobs.send_test_message.send(
                str(integration.league_id), integration.guild_id, integration.channel_id
            )
            return CommandResponse(
                content="✅ Test message queued! Check your announcement channel for a confirmation message.",
                ephemeral=True,
            )
        finally:
            session.close()
