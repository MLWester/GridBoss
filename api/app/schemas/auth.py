from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models import LeagueRole


class UserOut(BaseModel):
    id: UUID
    discord_id: str | None
    discord_username: str | None
    avatar_url: str | None
    email: str | None

    class Config:
        from_attributes = True


class MembershipOut(BaseModel):
    league_id: UUID
    league_slug: str
    league_name: str
    role: LeagueRole


class BillingPlanOut(BaseModel):
    plan: str | None
    current_period_end: datetime | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
    billingPlan: BillingPlanOut | None
