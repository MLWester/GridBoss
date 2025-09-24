from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class StandingsItem(BaseModel):
    driver_id: UUID
    display_name: str
    points: int
    wins: int
    best_finish: int | None


class SeasonStandingsRead(BaseModel):
    league_id: UUID
    season_id: UUID | None
    items: list[StandingsItem]
