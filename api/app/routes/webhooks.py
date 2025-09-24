from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import stripe

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.settings import Settings, get_settings
from app.db.models import BillingAccount, League, StripeEvent, Subscription
from app.db.session import get_session

try:
    from worker.jobs import stripe as stripe_jobs
except Exception:  # pragma: no cover - worker optional during testing
    stripe_jobs = None  # type: ignore

router = APIRouter(tags=["webhooks"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

PLAN_DRIVER_LIMITS = {"FREE": 20, "PRO": 100, "ELITE": 9999}


def _map_price_to_plan(price_id: str, settings: Settings) -> str | None:
    mapping = {
        settings.stripe_price_pro: "PRO",
        settings.stripe_price_elite: "ELITE",
    }
    return mapping.get(price_id)


def _update_leagues_for_plan(session: Session, billing_account: BillingAccount, plan: str) -> None:
    driver_limit = PLAN_DRIVER_LIMITS.get(plan, PLAN_DRIVER_LIMITS["FREE"])
    billing_account.plan = plan
    leagues = session.execute(
        select(League).where(League.owner_id == billing_account.owner_user_id)
    ).scalars().all()
    for league in leagues:
        league.plan = plan
        league.driver_limit = driver_limit


def _ensure_subscription(
    session: Session,
    *,
    billing_account: BillingAccount,
    subscription_id: str,
) -> Subscription:
    subscription = (
        session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        .scalars()
        .first()
    )
    if subscription is None:
        subscription = Subscription(
            billing_account_id=billing_account.id,
            stripe_subscription_id=subscription_id,
            plan=billing_account.plan,
            status="active",
        )
        session.add(subscription)
    return subscription


def _record_processed_event(session: Session, event_id: str) -> StripeEvent:
    event_row = StripeEvent(event_id=event_id)
    session.add(event_row)
    session.flush()
    return event_row


def _parse_timestamp(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _handle_checkout_completed(
    session: Session,
    *,
    payload: dict[str, object],
    settings: Settings,
) -> None:
    data_object = payload.get("data", {}).get("object", {})  # type: ignore[assignment]
    customer_id = data_object.get("customer") if isinstance(data_object, dict) else None
    subscription_id = data_object.get("subscription") if isinstance(data_object, dict) else None
    metadata = data_object.get("metadata") if isinstance(data_object, dict) else {}

    if not isinstance(customer_id, str):
        return

    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.stripe_customer_id == customer_id)
        )
        .scalars()
        .first()
    )
    if billing_account is None:
        return

    requested_plan = None
    if isinstance(metadata, dict):
        plan_value = metadata.get("plan")
        if isinstance(plan_value, str):
            requested_plan = plan_value.upper()

    if requested_plan not in {"PRO", "ELITE"}:
        price_id = metadata.get("price_id") if isinstance(metadata, dict) else None
        if isinstance(price_id, str):
            requested_plan = _map_price_to_plan(price_id, settings)

    if requested_plan:
        _update_leagues_for_plan(session, billing_account, requested_plan)

    if isinstance(subscription_id, str):
        subscription = _ensure_subscription(
            session,
            billing_account=billing_account,
            subscription_id=subscription_id,
        )
        if requested_plan:
            subscription.plan = requested_plan
        subscription.status = "active"


def _extract_price_plan(data: dict[str, object], settings: Settings) -> str | None:
    plan = None
    items = data.get("items") if isinstance(data, dict) else None
    if isinstance(items, dict):
        data_items = items.get("data")
        if isinstance(data_items, list) and data_items:
            first = data_items[0]
            if isinstance(first, dict):
                price = first.get("price")
                if isinstance(price, dict):
                    price_id = price.get("id")
                    if isinstance(price_id, str):
                        plan = _map_price_to_plan(price_id, settings)
    if plan is None:
        metadata = data.get("metadata") if isinstance(data, dict) else None
        if isinstance(metadata, dict):
            plan_value = metadata.get("plan")
            if isinstance(plan_value, str):
                plan = plan_value.upper()
    return plan


def _handle_subscription_update(
    session: Session,
    *,
    payload: dict[str, object],
    settings: Settings,
) -> None:
    data = payload.get("data", {}).get("object", {})  # type: ignore[assignment]
    if not isinstance(data, dict):
        return

    customer_id = data.get("customer")
    subscription_id = data.get("id")
    status = data.get("status")
    current_period_end = data.get("current_period_end")

    if not isinstance(customer_id, str) or not isinstance(subscription_id, str):
        return

    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.stripe_customer_id == customer_id)
        )
        .scalars()
        .first()
    )
    if billing_account is None:
        return

    subscription = _ensure_subscription(
        session,
        billing_account=billing_account,
        subscription_id=subscription_id,
    )

    plan = _extract_price_plan(data, settings)
    if plan:
        subscription.plan = plan
        _update_leagues_for_plan(session, billing_account, plan)

    if isinstance(status, str):
        subscription.status = status
    billing_account.current_period_end = _parse_timestamp(current_period_end if isinstance(current_period_end, int) else None)

    if stripe_jobs is not None:
        try:
            stripe_jobs.sync_plan_from_stripe.send(customer_id)
        except Exception:  # pragma: no cover - best effort
            pass


def _handle_subscription_deleted(session: Session, *, payload: dict[str, object], settings: Settings) -> None:
    data = payload.get("data", {}).get("object", {})  # type: ignore[assignment]
    if not isinstance(data, dict):
        return

    customer_id = data.get("customer")
    subscription_id = data.get("id")
    if not isinstance(customer_id, str) or not isinstance(subscription_id, str):
        return

    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.stripe_customer_id == customer_id)
        )
        .scalars()
        .first()
    )
    if billing_account is None:
        return

    subscription = (
        session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        .scalars()
        .first()
    )
    if subscription is not None:
        subscription.status = "canceled"

    _update_leagues_for_plan(session, billing_account, "FREE")


def _handle_invoice_payment_failed(session: Session, *, payload: dict[str, object], settings: Settings) -> None:
    data = payload.get("data", {}).get("object", {})  # type: ignore[assignment]
    if not isinstance(data, dict):
        return

    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    if not isinstance(customer_id, str) or not isinstance(subscription_id, str):
        return

    subscription = (
        session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        .scalars()
        .first()
    )
    if subscription is not None:
        subscription.status = "past_due"


EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "customer.subscription.updated": _handle_subscription_update,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.payment_failed": _handle_invoice_payment_failed,
}


@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    if not settings.stripe_webhook_secret:
        raise api_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="BILLING_CONFIG",
            message="Stripe webhook secret not configured",
        )
    if stripe_signature is None:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_SIGNATURE",
            message="Stripe signature header missing",
        )

    payload_bytes = await request.body()
    payload_str = payload_bytes.decode("utf-8")

    try:
        event = stripe.Webhook.construct_event(  # type: ignore[attr-defined]
            payload_str,
            stripe_signature,
            settings.stripe_webhook_secret,
        )
    except stripe.error.SignatureVerificationError:  # type: ignore[attr-defined]
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_SIGNATURE",
            message="Invalid Stripe signature",
        )

    event_id = event.get("id") if isinstance(event, dict) else None
    event_type = event.get("type") if isinstance(event, dict) else None
    if not isinstance(event_id, str) or not isinstance(event_type, str):
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_EVENT",
            message="Stripe event missing id or type",
        )

    existing = (
        session.execute(select(StripeEvent).where(StripeEvent.event_id == event_id))
        .scalars()
        .first()
    )
    if existing is not None:
        return {"status": "ignored"}

    try:
        recorded = _record_processed_event(session, event_id)
        handler = EVENT_HANDLERS.get(event_type)
        if handler is not None:
            handler(session, payload=event, settings=settings)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {"status": "processed"}