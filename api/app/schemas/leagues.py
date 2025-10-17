from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LeagueCreate(BaseModel):
    name: str
    slug: str
    description: str | None = Field(default=None, max_length=1000)


class LeagueUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = Field(default=None, max_length=1000)


class LeagueRead(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    driver_limit: int
    owner_id: UUID | None
    is_deleted: bool
    deleted_at: datetime | None
    description: str | None = None

    class Config:
        from_attributes = True
