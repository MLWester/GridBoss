from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LeagueCreate(BaseModel):
    name: str
    slug: str


class LeagueUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class LeagueRead(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    driver_limit: int
    owner_id: UUID | None
    is_deleted: bool
    deleted_at: datetime | None

    class Config:
        from_attributes = True
