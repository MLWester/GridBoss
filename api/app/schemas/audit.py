from __future__ import annotations

from datetime import datetime
from typing import Any, List
from uuid import UUID

from pydantic import BaseModel

from app.services.audit import redact_sensitive_data


class AuditLogRead(BaseModel):
    id: UUID
    timestamp: datetime
    actor_id: UUID | None
    league_id: UUID | None
    entity: str
    entity_id: str | None
    action: str
    before_state: Any | None
    after_state: Any | None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_redaction(cls, log: Any) -> "AuditLogRead":  # type: ignore[override]
        data = {
            "id": log.id,
            "timestamp": log.timestamp,
            "actor_id": log.actor_id,
            "league_id": log.league_id,
            "entity": log.entity,
            "entity_id": log.entity_id,
            "action": log.action,
            "before_state": redact_sensitive_data(log.before_state),
            "after_state": redact_sensitive_data(log.after_state),
        }
        return cls.model_validate(data)


class AuditLogPage(BaseModel):
    items: List[AuditLogRead]
    page: int
    page_size: int
    total: int

    class Config:
        populate_by_name = True


__all__ = ["AuditLogRead", "AuditLogPage"]
