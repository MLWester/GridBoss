from __future__ import annotations

import logging

import dramatiq

logger = logging.getLogger("worker.jobs.standings")


@dramatiq.actor(max_retries=3)
def recompute_standings(league_id: str, season_id: str | None) -> None:
    logger.info("Recompute standings job queued (league=%s, season=%s)", league_id, season_id)
