from __future__ import annotations

import logging

import dramatiq

logger = logging.getLogger("worker.jobs")


@dramatiq.actor(max_retries=0)
def heartbeat(message: str = "Worker heartbeat", *, context: str | None = None) -> None:
    """Log a heartbeat message so we can verify queue processing."""
    if context:
        logger.info("Heartbeat: %s (context=%s)", message, context)
    else:
        logger.info("Heartbeat: %s", message)
