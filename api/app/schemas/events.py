from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import EventStatus


class EventCreate(BaseModel):
    name: str = Field(min_length=1)
    track: str = Field(min_length=1)
    start_time: datetime
    season_id: UUID | None = None
    laps: int | None = Field(default=None, gt=0)
    distance_km: float | None = Field(default=None, gt=0)


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    track: str | None = Field(default=None, min_length=1)
    start_time: datetime | None = None
    season_id: UUID | None = None
    laps: int | None = Field(default=None, gt=0)
    distance_km: float | None = Field(default=None, gt=0)
    status: EventStatus | None = None


class EventRead(BaseModel):
    id: UUID
    league_id: UUID
    season_id: UUID | None
    name: str
    track: str
    start_time: datetime
    laps: int | None
    distance_km: float | None
    status: EventStatus

    class Config:
        from_attributes = True
