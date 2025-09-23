"""Dramatiq worker entrypoint for GridBoss."""

from __future__ import annotations

import logging
import signal
from types import FrameType

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import Retries
from dramatiq.worker import Worker

from worker.config import WorkerConfig, load_config

logger = logging.getLogger("worker")


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="[worker] %(message)s")


def _create_broker(config: WorkerConfig) -> RedisBroker:
    broker = RedisBroker(url=config.redis_url)

    def backoff(attempt: int) -> int:
        delay = config.retry_min_backoff_ms * (2 ** (attempt - 1))
        return min(delay, config.retry_max_backoff_ms)

    broker.add_middleware(
        Retries(
            max_retries=config.retry_max_retries,
            min_backoff=config.retry_min_backoff_ms,
            max_backoff=config.retry_max_backoff_ms,
            backoff=backoff,
        )
    )
    return broker


def main() -> None:
    _configure_logging()
    config = load_config()

    broker = _create_broker(config)
    dramatiq.set_broker(broker)

    # Import actors so Dramatiq registers them with the broker.
    from worker.jobs import heartbeat  # noqa: F401  # pylint: disable=unused-import

    worker = Worker(broker, worker_threads=config.worker_threads, worker_name=config.worker_name)

    def shutdown(signo: int, frame: FrameType | None) -> None:  # pragma: no cover - signal handler
        logger.info("Received signal %s, shutting down worker.", signo)
        worker.stop()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Worker starting with Redis broker at %s", config.redis_url)

    try:
        worker.start()
        worker.join()
    except KeyboardInterrupt:  # pragma: no cover - extra guard
        shutdown(signal.SIGINT, None)
    finally:
        logger.info("Worker stopped.")


if __name__ == "__main__":
    main()
