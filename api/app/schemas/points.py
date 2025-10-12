from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class PointsRuleInput(BaseModel):
    position: int = Field(gt=0)
    points: int = Field(ge=0)


class PointsRuleRead(BaseModel):
    id: UUID
    position: int
    points: int

    class Config:
        from_attributes = True


class PointsSchemeCreate(BaseModel):
    name: str = Field(min_length=1)
    season_id: UUID | None = None
    is_default: bool | None = False
    rules: list[PointsRuleInput] | None = None


class PointsSchemeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    season_id: UUID | None = None
    is_default: bool | None = None
    rules: list[PointsRuleInput] | None = None


class PointsSchemeRead(BaseModel):
    id: UUID
    league_id: UUID
    season_id: UUID | None
    name: str
    is_default: bool
    rules: list[PointsRuleRead]

    class Config:
        from_attributes = True
