from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.settings import Settings

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
_league_id: ContextVar[str | None] = ContextVar("league_id", default=None)


class JsonLogFormatter(logging.Formatter):
    """Render log records as JSON with standard observability fields."""

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(None),
            "user_id": _user_id.get(None),
            "league_id": _league_id.get(None),
        }

        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            base["stack"] = record.stack_info

        # merge structured extras that may live on the record
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in base or key in reserved:
                continue
            base[key] = value

        return json.dumps(base, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    level = logging.DEBUG if settings.app_env == "development" else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # This aligns standard FastAPI/uvicorn loggers with our JSON output when running under uvicorn.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = [handler]
        logging.getLogger(name).setLevel(level)


def bind_request_id(request_id: str | None) -> None:
    _request_id.set(request_id)


def bind_user_id(user_id: str | None) -> None:
    _user_id.set(user_id)


def bind_league_id(league_id: str | None) -> None:
    _league_id.set(league_id)


def get_request_id() -> str | None:
    return _request_id.get(None)


def clear_context() -> None:
    _request_id.set(None)
    _user_id.set(None)
    _league_id.set(None)
