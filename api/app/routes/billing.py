from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.settings import Settings, get_settings
from app.db.models import BillingAccount, Driver, League, LeagueRole, Membership, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.billing import (
    BillingLeagueUsage,
    BillingOverviewResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
)
from app.services.audit import record_audit_log
from app.services.plan import PLAN_DRIVER_LIMITS, normalize_plan
from app.services.stripe import StripeClient, StripeConfigurationError

router = APIRouter(tags=["billing"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def provide_stripe_client(settings: Settings = Depends(get_settings)) -> StripeClient:
    return StripeClient(settings.stripe_secret_key)


StripeClientDep = Annotated[StripeClient, Depends(provide_stripe_client)]

SUPPORTED_PLANS = {"PRO", "ELITE"}


def _owner_leagues(session: Session, user_id: str) -> list[League]:
    return (
        session.execute(select(League).where(League.owner_id == user_id)).scalars().all()
    )


def _ensure_owner_role(session: Session, user_id: str) -> None:
    membership = session.execute(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.role == LeagueRole.OWNER,
        )
    ).first()
    if membership is None:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="INSUFFICIENT_ROLE",
            message="Only league owners can manage billing",
        )


def _plan_price(plan: str, settings: Settings) -> str:
    if plan == "PRO":
        price = settings.stripe_price_pro
    else:
        price = settings.stripe_price_elite
    if not price:
        raise StripeConfigurationError("Stripe price IDs are not configured")
    return price


def _app_url(settings: Settings) -> str:
    return str(settings.app_url).rstrip("/")


@router.get("/billing/overview", response_model=BillingOverviewResponse)
async def read_billing_overview(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> BillingOverviewResponse:
    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.owner_user_id == current_user.id)
        )
        .scalars()
        .first()
    )

    leagues_query = (
        select(League, func.count(Driver.id))
        .outerjoin(Driver, Driver.league_id == League.id)
        .where(League.owner_id == current_user.id, League.is_deleted.is_(False))
        .group_by(League.id)
    )
    league_rows = session.execute(leagues_query).all()

    leagues = [
        BillingLeagueUsage(
            id=league.id,
            name=league.name,
            slug=league.slug,
            plan=normalize_plan(league.plan),
            driver_limit=league.driver_limit,
            driver_count=int(count or 0),
        )
        for league, count in league_rows
    ]

    plan = normalize_plan(billing_account.plan if billing_account else None)

    return BillingOverviewResponse(
        plan=plan,
        current_period_end=billing_account.current_period_end if billing_account else None,
        grace_plan=billing_account.plan_grace_plan if billing_account else None,
        grace_expires_at=billing_account.plan_grace_expires_at if billing_account else None,
        can_manage_subscription=bool(
            billing_account and billing_account.stripe_customer_id
        ),
        leagues=leagues,
    )


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    payload: CheckoutRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    stripe_client: StripeClientDep,
) -> CheckoutResponse:
    plan = payload.plan.upper()
    if plan not in SUPPORTED_PLANS:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PLAN",
            message="Plan must be PRO or ELITE",
        )

    _ensure_owner_role(session, current_user.id)

    leagues = _owner_leagues(session, current_user.id)
    if not leagues:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="NO_LEAGUES",
            message="Create a league before managing billing",
        )

    league_states_before = {
        league.id: {"plan": league.plan, "driver_limit": league.driver_limit}
        for league in leagues
    }

    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.owner_user_id == current_user.id)
        )
        .scalars()
        .first()
    )
    if billing_account is None:
        before_billing = None
        billing_account = BillingAccount(owner_user_id=current_user.id, plan=plan)
        session.add(billing_account)
    else:
        before_billing = {
            "plan": billing_account.plan,
            "plan_grace_plan": billing_account.plan_grace_plan,
            "plan_grace_expires_at": billing_account.plan_grace_expires_at,
        }

    price_id = _plan_price(plan, settings)
    try:
        customer_id = stripe_client.ensure_customer(
            customer_id=billing_account.stripe_customer_id,
            email=current_user.email,
        )
        base_url = _app_url(settings)
        checkout_url = stripe_client.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=f"{base_url}/billing/success",
            cancel_url=f"{base_url}/billing",
        )
    except StripeConfigurationError as exc:
        raise api_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="BILLING_CONFIG",
            message=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - Stripe SDK error
        raise api_error(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="STRIPE_ERROR",
            message="Unable to initiate checkout",
        ) from exc

    billing_account.stripe_customer_id = customer_id
    billing_account.plan = plan
    billing_account.plan_grace_plan = None
    billing_account.plan_grace_expires_at = None
    driver_limit = PLAN_DRIVER_LIMITS.get(plan, PLAN_DRIVER_LIMITS["FREE"])
    for league in leagues:
        league.plan = plan
        league.driver_limit = driver_limit

    session.flush()

    after_billing = {
        "plan": billing_account.plan,
        "plan_grace_plan": billing_account.plan_grace_plan,
        "plan_grace_expires_at": billing_account.plan_grace_expires_at,
    }
    if before_billing != after_billing:
        record_audit_log(
            session,
            actor_id=current_user.id,
            league_id=None,
            entity="billing_account",
            entity_id=str(billing_account.id),
            action="plan_checkout",
            before=before_billing,
            after=after_billing,
        )

    for league in leagues:
        before_state = league_states_before.get(league.id)
        after_state = {"plan": league.plan, "driver_limit": league.driver_limit}
        if before_state != after_state:
            record_audit_log(
                session,
                actor_id=current_user.id,
                league_id=league.id,
                entity="league",
                entity_id=str(league.id),
                action="plan_checkout",
                before=before_state,
                after=after_state,
            )

    session.commit()

    return CheckoutResponse(url=checkout_url)


@router.post("/billing/portal", response_model=PortalResponse)
async def create_portal_session(
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    stripe_client: StripeClientDep,
) -> PortalResponse:
    _ensure_owner_role(session, current_user.id)

    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.owner_user_id == current_user.id)
        )
        .scalars()
        .first()
    )
    if billing_account is None or not billing_account.stripe_customer_id:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BILLING_NOT_CONFIGURED",
            message="Billing account is not configured with a Stripe customer",
        )

    try:
        base_url = _app_url(settings)
        portal_url = stripe_client.create_billing_portal_session(
            customer_id=billing_account.stripe_customer_id,
            return_url=f"{base_url}/billing",
        )
    except StripeConfigurationError as exc:
        raise api_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="BILLING_CONFIG",
            message=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - Stripe SDK error
        raise api_error(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="STRIPE_ERROR",
            message="Unable to create billing portal session",
        ) from exc

    return PortalResponse(url=portal_url)
