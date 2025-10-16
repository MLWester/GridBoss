from __future__ import annotations

from dataclasses import dataclass

from gridboss_config import get_settings


@dataclass(frozen=True)
class WorkerConfig:
    redis_url: str
    worker_threads: int
    worker_name: str = "gridboss-worker"
    retry_max_retries: int = 5
    retry_min_backoff_ms: int = 1_000
    retry_max_backoff_ms: int = 300_000


def load_config() -> WorkerConfig:
    settings = get_settings()
    return WorkerConfig(
        redis_url=settings.redis_url,
        worker_threads=settings.worker_threads,
        worker_name=settings.worker_name,
        retry_max_retries=settings.worker_retry_max_retries,
        retry_min_backoff_ms=settings.worker_retry_min_backoff_ms,
        retry_max_backoff_ms=settings.worker_retry_max_backoff_ms,
    )
