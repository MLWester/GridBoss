from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.observability import configure_logging
from app.core.settings import get_settings
from app.db import Base
from app.middleware.request_context import RequestContextMiddleware
from app.routes import (
    admin,
    audit,
    auth,
    billing,
    discord,
    drivers,
    events,
    health,
    leagues,
    memberships,
    points,
    results,
    seasons,
    standings,
    teams,
    webhooks,
)

logger = logging.getLogger("app.main")


def _prepare_sqlite_defaults(app_env: str) -> None:
    if app_env == "production":
        return
    for table in Base.metadata.sorted_tables:
        for column in table.c:
            default = getattr(column, "server_default", None)
            if (
                default is not None
                and hasattr(default, "arg")
                and "gen_random_uuid" in str(default.arg)
            ):
                column.server_default = None


settings = get_settings()
_prepare_sqlite_defaults(settings.app_env)
configure_logging(settings)

app = FastAPI(title="GridBoss API", version="0.1.0")


@app.exception_handler(FastAPIHTTPException)
async def api_http_exception_handler(
    request: Request,
    exc: FastAPIHTTPException,
):
    detail = exc.detail
    if isinstance(detail, dict):
        if "error" in detail and isinstance(detail["error"], dict):
            return JSONResponse(status_code=exc.status_code, content=detail)
        if "code" in detail:
            return JSONResponse(status_code=exc.status_code, content={"error": detail})
    return await http_exception_handler(request, exc)


allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(RequestContextMiddleware)

app.include_router(health.router)
app.include_router(audit.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(leagues.router)
app.include_router(memberships.router)
app.include_router(drivers.router)
app.include_router(events.router)
app.include_router(results.router)
app.include_router(discord.router)
app.include_router(standings.router)
app.include_router(seasons.router)
app.include_router(points.router)
app.include_router(webhooks.router)
app.include_router(teams.router)


def _init_sentry() -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
    except Exception as exc:  # pragma: no cover - optional integration
        logger.warning("Sentry initialisation failed: %s", exc)


def _init_opentelemetry(api: FastAPI) -> None:
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        exporter = (
            OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
            if settings.otel_exporter_endpoint
            else OTLPSpanExporter()
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor().instrument_app(api)
        LoggingInstrumentor().instrument(set_logging_format=False)
    except Exception as exc:  # pragma: no cover - optional integration
        logger.warning("OpenTelemetry initialisation failed: %s", exc)


_init_sentry()
_init_opentelemetry(app)
