from __future__ import annotations

import logging

import dramatiq

logger = logging.getLogger("worker.jobs.discord")


@dramatiq.actor(max_retries=3)
def send_test_message(league_id: str, guild_id: str, channel_id: str) -> None:
    logger.info(
        "Discord test message queued (league=%s, guild=%s, channel=%s)",
        league_id,
        guild_id,
        channel_id,
    )
