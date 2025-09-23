from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DriverCreateItem(BaseModel):
    display_name: str = Field(min_length=1)
    team_id: UUID | None = None


class DriverBulkCreate(BaseModel):
    items: list[DriverCreateItem] = Field(min_length=1)


class DriverUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1)
    team_id: UUID | None = Field(default=None)


class DriverRead(BaseModel):
    id: UUID
    league_id: UUID
    display_name: str
    user_id: UUID | None
    discord_id: str | None
    team_id: UUID | None
    team_name: str | None

    class Config:
        from_attributes = True
