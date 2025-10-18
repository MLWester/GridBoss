from __future__ import annotations

import time
from typing import Annotated, Any

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.db.session import get_session

router = APIRouter(tags=["health"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


_ready_cache: tuple[float, dict[str, Any]] | None = None


def _check_database(session: Session) -> dict[str, Any]:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - unexpected driver failure
        return {"status": "error", "message": str(exc)}
    return {"status": "ok"}


def _check_migrations(session: Session) -> dict[str, Any]:
    try:
        result = session.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        if version:
            return {"status": "ok", "version": version}
        return {"status": "unknown", "message": "No migration version recorded"}
    except Exception as exc:
        # SQLite test databases will not have an alembic_version table by default
        return {"status": "unknown", "message": str(exc)}


def _check_redis(redis_url: str) -> dict[str, Any]:
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        try:
            client.ping()
        finally:
            try:
                client.close()
            except Exception:  # pragma: no cover - older redis versions
                pass
    except redis.RedisError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:  # pragma: no cover - optional redis dependency issues
        return {"status": "unknown", "message": str(exc)}
    return {"status": "ok"}


def _check_sentry(settings: Settings) -> dict[str, Any]:
    if not settings.sentry_dsn:
        return {"status": "skipped"}
    try:
        import sentry_sdk

        client = sentry_sdk.Hub.current.client  # type: ignore[attr-defined]
        if client is None:
            return {"status": "error", "message": "sentry client not initialised"}
    except ImportError:
        return {"status": "error", "message": "sentry-sdk not installed"}
    except Exception as exc:  # pragma: no cover - unexpected integration failure
        return {"status": "error", "message": str(exc)}
    return {"status": "ok"}


def _build_ready_payload(session: Session, settings: Settings) -> dict[str, Any]:
    database_check = _check_database(session)
    redis_check = _check_redis(settings.redis_url)
    migration_check = _check_migrations(session)
    sentry_check = _check_sentry(settings)

    checks = {
        "database": database_check,
        "redis": redis_check,
        "migrations": migration_check,
        "sentry": sentry_check,
    }
    overall = "ok" if not any(item["status"] == "error" for item in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


def clear_health_cache() -> None:
    global _ready_cache
    _ready_cache = None


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Lightweight health probe."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(session: SessionDep, settings: SettingsDep) -> dict[str, Any]:
    global _ready_cache
    ttl = max(settings.health_cache_seconds, 0)
    if ttl and _ready_cache is not None:
        cached_at, payload = _ready_cache
        if time.monotonic() - cached_at <= ttl:
            return payload

    payload = _build_ready_payload(session, settings)
    if ttl:
        _ready_cache = (time.monotonic(), payload)
    return payload


__all__ = ["router", "clear_health_cache"]
