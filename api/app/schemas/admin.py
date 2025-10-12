from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminUserSummary(BaseModel):
    id: UUID
    discord_username: str | None
    email: str | None
    created_at: datetime
    leagues_owned: int
    billing_plan: str
    subscription_status: str | None
    stripe_customer_id: str | None


class AdminLeagueSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    driver_limit: int
    driver_count: int
    owner_id: UUID | None
    owner_discord_username: str | None
    owner_email: str | None
    billing_plan: str
    discord_active: bool


class AdminSearchResponse(BaseModel):
    users: list[AdminUserSummary]
    leagues: list[AdminLeagueSummary]


class DiscordToggleRequest(BaseModel):
    is_active: bool


class PlanOverrideRequest(BaseModel):
    plan: str
