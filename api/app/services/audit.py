from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AuditLog

_REDACT_KEYWORDS = {"password", "secret", "token", "api_key", "webhook", "key"}


def _ensure_serialisable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _ensure_serialisable(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_ensure_serialisable(item) for item in value]
    return str(value)


def record_audit_log(
    session: Session,
    *,
    actor_id: UUID | None,
    league_id: UUID | None,
    entity: str,
    action: str,
    entity_id: str | None = None,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor_id,
        league_id=league_id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        before_state=_ensure_serialisable(before) if before is not None else None,
        after_state=_ensure_serialisable(after) if after is not None else None,
    )
    session.add(log)
    session.flush()
    return log


def _redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if any(keyword in key.lower() for keyword in _REDACT_KEYWORDS):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = redact_sensitive_data(value)
    return redacted


def redact_sensitive_data(data: Any) -> Any:
    if data is None:
        return None
    if isinstance(data, Mapping):
        return _redact_mapping(data)
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        return [redact_sensitive_data(item) for item in data]
    return data


__all__ = ["record_audit_log", "redact_sensitive_data"]
