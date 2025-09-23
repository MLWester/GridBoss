from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkerConfig:
    redis_url: str
    worker_threads: int
    worker_name: str = "gridboss-worker"
    retry_max_retries: int = 5
    retry_min_backoff_ms: int = 1_000
    retry_max_backoff_ms: int = 300_000


def load_config() -> WorkerConfig:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    worker_threads = int(os.getenv("WORKER_THREADS", "8"))
    worker_name = os.getenv("WORKER_NAME", "gridboss-worker")
    retry_min_backoff_ms = int(os.getenv("WORKER_RETRY_MIN_BACKOFF_MS", "1000"))
    retry_max_backoff_ms = int(os.getenv("WORKER_RETRY_MAX_BACKOFF_MS", "300000"))
    retry_max_retries = int(os.getenv("WORKER_RETRY_MAX_RETRIES", "5"))

    return WorkerConfig(
        redis_url=redis_url,
        worker_threads=worker_threads,
        worker_name=worker_name,
        retry_max_retries=retry_max_retries,
        retry_min_backoff_ms=retry_min_backoff_ms,
        retry_max_backoff_ms=retry_max_backoff_ms,
    )
