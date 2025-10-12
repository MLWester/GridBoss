from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import ResultStatus


class ResultEntryCreate(BaseModel):
    driver_id: UUID
    finish_position: int = Field(gt=0)
    started_position: int | None = Field(default=None, ge=1)
    status: ResultStatus = ResultStatus.FINISHED
    bonus_points: int = Field(default=0)
    penalty_points: int = Field(default=0)


class ResultSubmission(BaseModel):
    entries: list[ResultEntryCreate] = Field(min_length=1)


class ResultEntryRead(BaseModel):
    driver_id: UUID
    finish_position: int
    started_position: int | None
    status: ResultStatus
    bonus_points: int
    penalty_points: int
    total_points: int


class EventResultsRead(BaseModel):
    event_id: UUID
    league_id: UUID
    season_id: UUID | None
    items: list[ResultEntryRead]
