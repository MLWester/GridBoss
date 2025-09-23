from __future__ import annotations

import logging

import dramatiq

logger = logging.getLogger("worker.jobs.standings")


@dramatiq.actor(max_retries=3)
def recompute_standings(league_id: str, season_id: str | None) -> None:
    logger.info("Recompute standings job queued (league=%s, season=%s)", league_id, season_id)


@dramatiq.actor(max_retries=3)
def announce_results(league_id: str, event_id: str) -> None:
    logger.info("Announce results job queued (league=%s, event=%s)", league_id, event_id)
