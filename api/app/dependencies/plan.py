from __future__ import annotations

from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.models import League
from app.services.plan import (
    effective_plan,
    get_billing_account_for_owner,
    is_plan_sufficient,
)


def _resolve_league(session: Session, kwargs: dict[str, Any]) -> League:
    league = kwargs.get("league")
    if isinstance(league, League):
        return league

    league_id = kwargs.get("league_id")
    if league_id is None:
        raise RuntimeError("requires_plan decorator expects 'league' or 'league_id' arguments")

    if not isinstance(league_id, UUID):
        try:
            league_id = UUID(str(league_id))
        except (TypeError, ValueError) as exc:
            raise api_error(
                status_code=status.HTTP_404_NOT_FOUND,
                code="LEAGUE_NOT_FOUND",
                message="League not found",
            ) from exc

    league_obj = session.get(League, league_id)
    if league_obj is None or league_obj.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )

    return league_obj


def _ensure_plan_access(
    *,
    session: Session,
    league: League,
    required_plan: str,
    message: str | None,
) -> None:
    billing_account = get_billing_account_for_owner(session, league.owner_id)
    current_plan = effective_plan(league.plan, billing_account)
    if not is_plan_sufficient(current_plan, required_plan):
        detail = message or f"This action requires the {required_plan.title()} plan"
        raise api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="PLAN_LIMIT",
            message=detail,
        )


def requires_plan(required_plan: str, *, message: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    normalized_required = required_plan.upper()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                session = kwargs.get("session")
                if session is None:
                    raise RuntimeError("requires_plan decorator expects a 'session' argument")
                league = _resolve_league(session, kwargs)
                _ensure_plan_access(
                    session=session,
                    league=league,
                    required_plan=normalized_required,
                    message=message,
                )
                return await func(*args, **kwargs)

            async_wrapper.__globals__.update(func.__globals__)
            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            session = kwargs.get("session")
            if session is None:
                raise RuntimeError("requires_plan decorator expects a 'session' argument")
            league = _resolve_league(session, kwargs)
            _ensure_plan_access(
                session=session,
                league=league,
                required_plan=normalized_required,
                message=message,
            )
            return func(*args, **kwargs)

        sync_wrapper.__globals__.update(func.__globals__)
        return sync_wrapper

    return decorator


__all__ = ["requires_plan"]
