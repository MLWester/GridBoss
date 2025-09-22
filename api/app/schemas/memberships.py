from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.db.models import LeagueRole


class MembershipCreate(BaseModel):
    user_id: UUID
    role: LeagueRole


class MembershipUpdate(BaseModel):
    role: LeagueRole


class MembershipRead(BaseModel):
    id: UUID
    league_id: UUID
    user_id: UUID
    role: LeagueRole

    class Config:
        from_attributes = True
