from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: str = Field(min_length=1)


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)


class TeamRead(BaseModel):
    id: UUID
    league_id: UUID
    name: str
    driver_count: int

    class Config:
        from_attributes = True
