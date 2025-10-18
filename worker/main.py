"""Dramatiq worker entrypoint for GridBoss."""

from __future__ import annotations

import logging
import signal
import time
from types import FrameType

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import Retries
from dramatiq.worker import Worker

from app.core.observability import configure_logging
from app.core.settings import Settings, get_settings
from worker.config import WorkerConfig, load_config

logger = logging.getLogger("worker")


def _init_sentry(settings: Settings) -> bool:
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
        )
        logger.info("Sentry initialised for worker.")
        return True
    except Exception as exc:  # pragma: no cover - optional integration
        logger.warning("Sentry initialisation failed: %s", exc)
        return False


def _init_opentelemetry(settings: Settings) -> bool:
    if not settings.otel_enabled:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        service_name = f"{settings.otel_service_name}-worker" if settings.otel_service_name else "gridboss-worker"
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = (
            OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
            if settings.otel_exporter_endpoint
            else OTLPSpanExporter()
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        LoggingInstrumentor().instrument(set_logging_format=False)
        logger.info("OpenTelemetry initialised for worker (service=%s).", service_name)
        return True
    except Exception as exc:  # pragma: no cover - optional integration
        logger.warning("OpenTelemetry initialisation failed: %s", exc)
        return False


def _create_broker(config: WorkerConfig) -> RedisBroker:
    broker = RedisBroker(url=config.redis_url)

    # Dramatiq's Prometheus middleware expects metrics added in newer releases; disable it for now.
    for middleware in list(broker.middleware):
        if middleware.__class__.__name__ == "Prometheus":
            broker.middleware.remove(middleware)

    broker.add_middleware(
        Retries(
            max_retries=config.retry_max_retries,
            min_backoff=config.retry_min_backoff_ms,
            max_backoff=config.retry_max_backoff_ms,
        )
    )
    return broker


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    _init_sentry(settings)
    _init_opentelemetry(settings)

    config = load_config()

    broker = _create_broker(config)
    dramatiq.set_broker(broker)

    # Import actors so Dramatiq registers them with the broker.
    from worker.jobs import (  # noqa: F401  # pylint: disable=unused-import
        announce_results,
        heartbeat,
        recompute_standings,
        send_test_message,
        send_transactional_email,
        sync_plan_from_stripe,
    )

    worker = Worker(broker, worker_threads=config.worker_threads)
    worker.worker_name = config.worker_name

    def shutdown(signo: int, frame: FrameType | None) -> None:  # pragma: no cover - signal handler
        logger.info("Received signal %s, shutting down worker.", signo)
        worker.stop()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Worker starting with Redis broker at %s", config.redis_url)

    worker.start()
    logger.info("Worker running with Redis broker at %s", config.redis_url)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:  # pragma: no cover - extra guard
        shutdown(signal.SIGINT, None)
    finally:
        worker.join()
        logger.info("Worker stopped.")


if __name__ == "__main__":
    main()


