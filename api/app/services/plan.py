from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BillingAccount, League

PLAN_DRIVER_LIMITS: Final[dict[str, int]] = {"FREE": 20, "PRO": 100, "ELITE": 9999}
_PLAN_ORDER: Final[tuple[str, ...]] = ("FREE", "PRO", "ELITE")
DEFAULT_PLAN: Final[str] = "FREE"
GRACE_PERIOD_DAYS: Final[int] = 7


def normalize_plan(plan: str | None) -> str:
    if not plan:
        return DEFAULT_PLAN
    return plan.upper()


def _plan_rank(plan: str | None) -> int:
    normalized = normalize_plan(plan)
    try:
        return _PLAN_ORDER.index(normalized)
    except ValueError:
        return _PLAN_ORDER.index(DEFAULT_PLAN)


def is_plan_sufficient(current: str | None, required: str) -> bool:
    return _plan_rank(current) >= _plan_rank(required)


def _max_plan(*plans: str | None) -> str:
    best = DEFAULT_PLAN
    for plan in plans:
        normalized = normalize_plan(plan)
        if _plan_rank(normalized) > _plan_rank(best):
            best = normalized
    return best


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def effective_plan(
    league_plan: str | None,
    billing_account: BillingAccount | None,
    *,
    now: datetime | None = None,
) -> str:
    current = normalize_plan(league_plan)
    if billing_account is not None:
        current = _max_plan(current, billing_account.plan)
        grace_plan = billing_account.plan_grace_plan
        expires_at = _ensure_utc(billing_account.plan_grace_expires_at)
        if grace_plan and expires_at:
            reference = _ensure_utc(now) or datetime.now(UTC)
            if expires_at > reference:
                current = _max_plan(current, grace_plan)
    return current


def effective_driver_limit(
    league: League,
    billing_account: BillingAccount | None,
    *,
    now: datetime | None = None,
) -> int:
    limit = league.driver_limit
    if billing_account is not None:
        expires_at = _ensure_utc(billing_account.plan_grace_expires_at)
        grace_plan = billing_account.plan_grace_plan
        if grace_plan and expires_at:
            reference = _ensure_utc(now) or datetime.now(UTC)
            if expires_at > reference:
                grace_limit = PLAN_DRIVER_LIMITS.get(
                    normalize_plan(grace_plan), PLAN_DRIVER_LIMITS[DEFAULT_PLAN]
                )
                limit = max(limit, grace_limit)
    return limit


def get_billing_account_for_owner(
    session: Session,
    owner_id: UUID,
) -> BillingAccount | None:
    return (
        session.execute(select(BillingAccount).where(BillingAccount.owner_user_id == owner_id))
        .scalars()
        .first()
    )


__all__ = [
    "DEFAULT_PLAN",
    "GRACE_PERIOD_DAYS",
    "PLAN_DRIVER_LIMITS",
    "effective_driver_limit",
    "effective_plan",
    "get_billing_account_for_owner",
    "is_plan_sufficient",
    "normalize_plan",
]
