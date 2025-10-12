from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel


class CheckoutRequest(BaseModel):
    plan: Literal["PRO", "ELITE"]


class CheckoutResponse(BaseModel):
    url: AnyHttpUrl


class PortalResponse(BaseModel):
    url: AnyHttpUrl


class BillingLeagueUsage(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    driver_limit: int
    driver_count: int


class BillingOverviewResponse(BaseModel):
    plan: str
    current_period_end: datetime | None
    grace_plan: str | None
    grace_expires_at: datetime | None
    can_manage_subscription: bool
    leagues: list[BillingLeagueUsage]
