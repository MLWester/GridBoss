from __future__ import annotations

import logging

import dramatiq

logger = logging.getLogger("worker.jobs.stripe")


@dramatiq.actor(max_retries=3)
def sync_plan_from_stripe(customer_id: str) -> None:
    logger.info("Sync plan from Stripe queued (customer=%s)", customer_id)
