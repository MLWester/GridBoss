from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.settings import Settings, get_settings
from app.db.models import BillingAccount, DiscordIntegration, Driver, League, Subscription, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.admin import (
    AdminLeagueSummary,
    AdminSearchResponse,
    AdminUserSummary,
    DiscordToggleRequest,
    PlanOverrideRequest,
)
from app.services.audit import record_audit_log
from app.services.plan import PLAN_DRIVER_LIMITS, normalize_plan

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

router = APIRouter(prefix="/admin", tags=["admin"])


def _ensure_admin_access(settings: Settings, user: User) -> None:
    if not settings.admin_mode:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ADMIN_DISABLED",
            message="Admin console is not enabled",
        )
    if not user.is_founder:
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FOUNDER_ACCESS_REQUIRED",
            message="Founder role required for admin console",
        )


def _collect_user_summaries(
    session: Session,
    rows: list[tuple[User, UUID | None, str | None, str | None]],
) -> list[AdminUserSummary]:
    if not rows:
        return []

    user_ids = {user.id for user, *_ in rows}
    billing_account_ids = {account_id for _, account_id, _, _ in rows if account_id is not None}

    league_counts: dict[UUID, int] = {}
    if user_ids:
        counts = session.execute(
            select(League.owner_id, func.count(League.id))
            .where(League.owner_id.in_(user_ids), League.is_deleted.is_(False))
            .group_by(League.owner_id)
        ).all()
        league_counts = {owner_id: int(count) for owner_id, count in counts}

    subscription_status: dict[UUID, str] = {}
    if billing_account_ids:
        status_rows = session.execute(
            select(
                Subscription.billing_account_id,
                Subscription.status,
                Subscription.started_at,
            )
            .where(Subscription.billing_account_id.in_(billing_account_ids))
            .order_by(
                Subscription.billing_account_id,
                Subscription.started_at.desc(),
            )
        ).all()
        for account_id, status_value, _ in status_rows:
            if account_id not in subscription_status:
                subscription_status[account_id] = status_value

    summaries: list[AdminUserSummary] = []
    seen_users: set[UUID] = set()
    for user, account_id, plan, stripe_customer_id in rows:
        if user.id in seen_users:
            continue
        seen_users.add(user.id)
        normalized_plan = normalize_plan(plan)
        summaries.append(
            AdminUserSummary(
                id=user.id,
                discord_username=user.discord_username,
                email=user.email,
                created_at=user.created_at,
                leagues_owned=league_counts.get(user.id, 0),
                billing_plan=normalized_plan,
                subscription_status=subscription_status.get(account_id) if account_id else None,
                stripe_customer_id=stripe_customer_id,
            )
        )

    return summaries


def _collect_league_summaries(
    session: Session,
    rows: list[tuple[League, str | None, str | None, str | None]],
) -> list[AdminLeagueSummary]:
    if not rows:
        return []

    league_ids = {league.id for league, *_ in rows}

    driver_counts: dict[UUID, int] = {}
    if league_ids:
        counts = session.execute(
            select(Driver.league_id, func.count(Driver.id))
            .where(Driver.league_id.in_(league_ids))
            .group_by(Driver.league_id)
        ).all()
        driver_counts = {league_id: int(count) for league_id, count in counts}

    integrations: dict[UUID, bool] = {}
    if league_ids:
        integration_rows = session.execute(
            select(DiscordIntegration.league_id, DiscordIntegration.is_active).where(
                DiscordIntegration.league_id.in_(league_ids)
            )
        ).all()
        integrations = {
            league_id: bool(is_active) if is_active is not None else False
            for league_id, is_active in integration_rows
        }

    summaries: list[AdminLeagueSummary] = []
    processed_leagues: set[UUID] = set()
    for league, owner_username, owner_email, billing_plan in rows:
        if league.id in processed_leagues:
            continue
        processed_leagues.add(league.id)
        normalized_plan = normalize_plan(league.plan)
        account_plan = normalize_plan(billing_plan if billing_plan else league.plan)
        summaries.append(
            AdminLeagueSummary(
                id=league.id,
                name=league.name,
                slug=league.slug,
                plan=normalized_plan,
                driver_limit=league.driver_limit,
                driver_count=driver_counts.get(league.id, 0),
                owner_id=league.owner_id,
                owner_discord_username=owner_username,
                owner_email=owner_email,
                billing_plan=account_plan,
                discord_active=integrations.get(league.id, False),
            )
        )

    return summaries


def _league_summary(session: Session, league: League) -> AdminLeagueSummary:
    driver_count = session.execute(
        select(func.count(Driver.id)).where(Driver.league_id == league.id)
    ).scalar_one()

    owner = session.get(User, league.owner_id) if league.owner_id else None
    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.owner_user_id == league.owner_id)
        )
        .scalars()
        .first()
        if league.owner_id
        else None
    )
    integration = (
        session.execute(select(DiscordIntegration).where(DiscordIntegration.league_id == league.id))
        .scalars()
        .first()
    )

    return AdminLeagueSummary(
        id=league.id,
        name=league.name,
        slug=league.slug,
        plan=normalize_plan(league.plan),
        driver_limit=league.driver_limit,
        driver_count=int(driver_count),
        owner_id=league.owner_id,
        owner_discord_username=owner.discord_username if owner else None,
        owner_email=owner.email if owner else None,
        billing_plan=normalize_plan(billing_account.plan if billing_account else league.plan),
        discord_active=bool(integration.is_active) if integration else False,
    )


@router.get("/search", response_model=AdminSearchResponse)
async def search_admin_resources(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    query: str | None = None,
) -> AdminSearchResponse:
    _ensure_admin_access(settings, current_user)

    pattern = f"%{query.strip()}%" if query and query.strip() else None
    limit = 25

    user_stmt = select(
        User,
        BillingAccount.id,
        BillingAccount.plan,
        BillingAccount.stripe_customer_id,
    ).outerjoin(BillingAccount, BillingAccount.owner_user_id == User.id)
    if pattern:
        user_stmt = user_stmt.where(
            or_(
                User.discord_username.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    user_stmt = user_stmt.order_by(User.created_at.desc()).limit(limit)
    user_rows = session.execute(user_stmt).all()

    league_stmt = (
        select(
            League,
            User.discord_username,
            User.email,
            BillingAccount.plan,
        )
        .outerjoin(User, User.id == League.owner_id)
        .outerjoin(BillingAccount, BillingAccount.owner_user_id == League.owner_id)
        .where(League.is_deleted.is_(False))
    )
    if pattern:
        league_stmt = league_stmt.where(
            or_(
                League.name.ilike(pattern),
                League.slug.ilike(pattern),
            )
        )
    league_stmt = league_stmt.order_by(League.created_at.desc()).limit(limit)
    league_rows = session.execute(league_stmt).all()

    # Ensure owners of matched leagues appear in user results
    owner_ids = {league.owner_id for league, *_ in league_rows if league.owner_id is not None}
    existing_user_ids = {row[0].id for row in user_rows}
    missing_owner_ids = owner_ids.difference(existing_user_ids)
    if missing_owner_ids:
        owner_stmt = (
            select(
                User,
                BillingAccount.id,
                BillingAccount.plan,
                BillingAccount.stripe_customer_id,
            )
            .outerjoin(BillingAccount, BillingAccount.owner_user_id == User.id)
            .where(User.id.in_(missing_owner_ids))
        )
        user_rows.extend(session.execute(owner_stmt).all())

    users = _collect_user_summaries(session, user_rows)
    leagues = _collect_league_summaries(session, league_rows)

    return AdminSearchResponse(users=users, leagues=leagues)


@router.post(
    "/leagues/{league_id}/discord/toggle",
    response_model=AdminLeagueSummary,
)
async def admin_toggle_discord_integration(
    league_id: UUID,
    payload: DiscordToggleRequest,
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
) -> AdminLeagueSummary:
    _ensure_admin_access(settings, current_user)

    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )

    integration = (
        session.execute(select(DiscordIntegration).where(DiscordIntegration.league_id == league_id))
        .scalars()
        .first()
    )
    if integration is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DISCORD_NOT_LINKED",
            message="Discord integration is not configured for this league",
        )

    before_state = {"is_active": integration.is_active}
    integration.is_active = payload.is_active
    session.flush()

    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league_id,
        entity="discord_integration",
        entity_id=str(integration.id),
        action="admin_discord_toggle",
        before=before_state,
        after={"is_active": integration.is_active},
    )

    session.commit()
    session.refresh(league)
    return _league_summary(session, league)


@router.post(
    "/leagues/{league_id}/plan",
    response_model=AdminLeagueSummary,
)
async def admin_override_plan(
    league_id: UUID,
    payload: PlanOverrideRequest,
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
) -> AdminLeagueSummary:
    _ensure_admin_access(settings, current_user)

    if settings.app_env == "production":
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="PLAN_OVERRIDE_DISABLED",
            message="Plan override is disabled in production environments",
        )

    requested_plan = normalize_plan(payload.plan)
    if requested_plan not in PLAN_DRIVER_LIMITS:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PLAN",
            message="Plan must be one of FREE, PRO, or ELITE",
        )

    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    if league.owner_id is None:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="LEAGUE_OWNER_MISSING",
            message="League owner is required to override plan",
        )

    driver_limit = PLAN_DRIVER_LIMITS[requested_plan]
    before_league = {"plan": league.plan, "driver_limit": league.driver_limit}
    league.plan = requested_plan
    league.driver_limit = driver_limit

    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league.id,
        entity="league",
        entity_id=str(league.id),
        action="admin_plan_override",
        before=before_league,
        after={"plan": league.plan, "driver_limit": league.driver_limit},
    )

    billing_account = (
        session.execute(
            select(BillingAccount).where(BillingAccount.owner_user_id == league.owner_id)
        )
        .scalars()
        .first()
    )
    if billing_account is None:
        billing_account = BillingAccount(owner_user_id=league.owner_id, plan=requested_plan)
        session.add(billing_account)
        session.flush()

    before_billing = {
        "plan": billing_account.plan,
        "plan_grace_plan": billing_account.plan_grace_plan,
        "plan_grace_expires_at": billing_account.plan_grace_expires_at,
    }
    billing_account.plan = requested_plan
    billing_account.plan_grace_plan = None
    billing_account.plan_grace_expires_at = None

    if before_billing != {
        "plan": billing_account.plan,
        "plan_grace_plan": billing_account.plan_grace_plan,
        "plan_grace_expires_at": billing_account.plan_grace_expires_at,
    }:
        record_audit_log(
            session,
            actor_id=current_user.id,
            league_id=None,
            entity="billing_account",
            entity_id=str(billing_account.id),
            action="admin_plan_override",
            before=before_billing,
            after={
                "plan": billing_account.plan,
                "plan_grace_plan": billing_account.plan_grace_plan,
                "plan_grace_expires_at": billing_account.plan_grace_expires_at,
            },
        )

    owner_leagues = session.execute(
        select(League)
        .where(League.owner_id == league.owner_id, League.is_deleted.is_(False))
        .order_by(League.created_at.asc())
    ).scalars()

    for owner_league in owner_leagues:
        if owner_league.id == league.id:
            continue
        previous = {
            "plan": owner_league.plan,
            "driver_limit": owner_league.driver_limit,
        }
        if previous["plan"] == requested_plan and previous["driver_limit"] == driver_limit:
            continue
        owner_league.plan = requested_plan
        owner_league.driver_limit = driver_limit
        record_audit_log(
            session,
            actor_id=current_user.id,
            league_id=owner_league.id,
            entity="league",
            entity_id=str(owner_league.id),
            action="admin_plan_override",
            before=previous,
            after={
                "plan": owner_league.plan,
                "driver_limit": owner_league.driver_limit,
            },
        )

    session.commit()
    session.refresh(league)
    return _league_summary(session, league)
