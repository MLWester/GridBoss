from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SeasonCreate(BaseModel):
    name: str = Field(min_length=1)
    is_active: bool | None = False


class SeasonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class SeasonRead(BaseModel):
    id: UUID
    league_id: UUID
    name: str
    is_active: bool

    class Config:
        from_attributes = True
