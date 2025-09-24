"""GridBoss Discord bot entrypoint."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

try:
    import discord
    from discord import app_commands
except ImportError:  # pragma: no cover - library optional in test env
    discord = None  # type: ignore
    app_commands = None  # type: ignore

from bot.config import BotConfig, load_config
from bot.service import CommandResponse, GridBossBot, InteractionContext

logging.basicConfig(level=logging.INFO, format="[bot] %(message)s")
logger = logging.getLogger("gridboss.bot")


def _interaction_context(interaction: "discord.Interaction", *, is_admin: bool) -> InteractionContext:
    guild_id = str(interaction.guild_id or getattr(interaction.guild, "id", "unknown"))
    channel_id = str(interaction.channel_id or getattr(interaction.channel, "id", "unknown"))
    user_id = str(interaction.user.id if interaction.user else "unknown")
    return InteractionContext(guild_id=guild_id, channel_id=channel_id, user_id=user_id, is_admin=is_admin)


def _is_admin(interaction: "discord.Interaction") -> bool:
    perms = getattr(interaction.user, "guild_permissions", None)
    if perms is None:
        return False
    return bool(getattr(perms, "administrator", False) or getattr(perms, "manage_guild", False))


async def _handle_interaction(
    bot_app: GridBossBot,
    interaction: "discord.Interaction",
    command: str,
) -> None:
    is_admin = _is_admin(interaction)
    context = _interaction_context(interaction, is_admin=is_admin)
    response: CommandResponse = bot_app.process_command(command, context)
    await interaction.response.send_message(response.content, ephemeral=response.ephemeral)


def _run_discord_bot(config: BotConfig, bot_app: GridBossBot) -> None:
    if discord is None or app_commands is None:
        logger.warning("discord.py is not installed. Falling back to no-op loop.")
        _run_noop_loop()
        return
    if not config.token:
        logger.warning("DISCORD_BOT_TOKEN is not configured.")
        _run_noop_loop()
        return

    class GridBossDiscordClient(discord.Client):  # type: ignore[misc]
        def __init__(self) -> None:
            intents = discord.Intents.none()
            super().__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)

        async def setup_hook(self) -> None:  # pragma: no cover - requires discord runtime
            gridboss_group = app_commands.Group(name="gridboss", description="GridBoss utilities")

            @gridboss_group.command(name="link", description="Generate a link to connect this guild to GridBoss")
            async def link_command(interaction: discord.Interaction) -> None:  # type: ignore[valid-type]
                await _handle_interaction(bot_app, interaction, "link")

            @gridboss_group.command(name="test", description="Send a test announcement to the configured channel")
            async def test_command(interaction: discord.Interaction) -> None:  # type: ignore[valid-type]
                await _handle_interaction(bot_app, interaction, "test")

            self.tree.add_command(gridboss_group)
            await self.tree.sync()
            logger.info("Slash commands synced with Discord")

        async def on_ready(self) -> None:  # pragma: no cover - requires discord runtime
            logger.info("GridBoss bot connected as %s", self.user)

    client = GridBossDiscordClient()
    client.run(config.token)


def _run_noop_loop() -> None:
    logger.info("GridBoss bot idle. Install discord.py and configure DISCORD_BOT_TOKEN to enable full functionality.")
    try:
        asyncio.run(_idle())
    except KeyboardInterrupt:
        logger.info("Discord bot stopping.")


async def _idle() -> None:
    while True:  # pragma: no cover - manual stop required
        await asyncio.sleep(60)


def main() -> None:
    config = load_config()
    bot_app = GridBossBot(config)
    _run_discord_bot(config, bot_app)


if __name__ == "__main__":
    main()
