from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.core.errors import api_error
from app.core.observability import bind_league_id
from app.db.models import Event, League, LeagueRole, PointsRule, PointsScheme, Season, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.points import (
    PointsRuleInput,
    PointsRuleRead,
    PointsSchemeCreate,
    PointsSchemeRead,
    PointsSchemeUpdate,
)
from app.services.audit import record_audit_log
from app.services.points import default_points_entries, normalize_points_entries
from app.services.rbac import require_membership, require_role_at_least

router = APIRouter(tags=["points"])

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


DEFAULT_RULE_LIMIT = 20


def _season_predicate(season_id: UUID | None):
    return (
        PointsScheme.season_id.is_(None)
        if season_id is None
        else PointsScheme.season_id == season_id
    )


def _get_league(session: Session, league_id: UUID) -> League:
    league = session.get(League, league_id)
    if league is None or league.is_deleted:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="LEAGUE_NOT_FOUND",
            message="League not found",
        )
    bind_league_id(str(league.id))
    return league


def _scheme_to_read(scheme: PointsScheme) -> PointsSchemeRead:
    return PointsSchemeRead(
        id=scheme.id,
        league_id=scheme.league_id,
        season_id=scheme.season_id,
        name=scheme.name,
        is_default=scheme.is_default,
        rules=[
            PointsRuleRead.model_validate(rule)
            for rule in sorted(scheme.rules, key=lambda r: r.position)
        ],
    )


def _validate_rules(rules: list[PointsRuleInput] | None) -> list[tuple[int, int]]:
    entries: list[tuple[int, int]]
    if not rules:
        entries = default_points_entries()
    else:
        raw_entries = [(item.position, item.points) for item in rules]
        try:
            entries = normalize_points_entries(raw_entries)
        except ValueError as exc:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="DUPLICATE_POSITION",
                message="Points table contains duplicate positions",
            ) from exc
    if len(entries) > DEFAULT_RULE_LIMIT:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="TOO_MANY_POSITIONS",
            message="Points table exceeds supported positions",
        )
    return entries


def _ensure_season(session: Session, *, league_id: UUID, season_id: UUID | None) -> UUID | None:
    if season_id is None:
        return None
    season = session.get(Season, season_id)
    if season is None or season.league_id != league_id:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_SEASON",
            message="Season does not belong to this league",
            field="season_id",
        )
    return season_id


def _set_rules_for_scheme(scheme: PointsScheme, entries: list[tuple[int, int]]) -> None:
    scheme.rules[:] = [PointsRule(position=position, points=points) for position, points in entries]


def _scheme_state(scheme: PointsScheme) -> dict[str, object]:
    return {
        "id": str(scheme.id),
        "name": scheme.name,
        "season_id": str(scheme.season_id) if scheme.season_id else None,
        "is_default": scheme.is_default,
        "rules": [
            {"position": rule.position, "points": rule.points}
            for rule in sorted(scheme.rules, key=lambda r: r.position)
        ],
    }


@router.get(
    "/leagues/{league_id}/points-schemes",
    response_model=list[PointsSchemeRead],
)
async def list_points_schemes(
    league_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[PointsSchemeRead]:
    _get_league(session, league_id)
    require_membership(session, league_id=league_id, user_id=current_user.id)

    schemes = (
        session.execute(
            select(PointsScheme)
            .options(joinedload(PointsScheme.rules))
            .where(PointsScheme.league_id == league_id)
            .order_by(PointsScheme.name)
        )
        .scalars()
        .all()
    )
    return [_scheme_to_read(scheme) for scheme in schemes]


@router.post(
    "/leagues/{league_id}/points-schemes",
    response_model=PointsSchemeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_points_scheme(
    league_id: UUID,
    payload: PointsSchemeCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> PointsSchemeRead:
    _get_league(session, league_id)
    membership = require_membership(session, league_id=league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    name = payload.name.strip()
    if not name:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_NAME",
            message="Points scheme name is required",
            field="name",
        )

    season_id = _ensure_season(session, league_id=league_id, season_id=payload.season_id)
    entries = _validate_rules(payload.rules)

    scheme = PointsScheme(
        league_id=league_id,
        season_id=season_id,
        name=name,
        is_default=bool(payload.is_default),
    )
    _set_rules_for_scheme(scheme, entries)
    session.add(scheme)
    session.flush()

    if scheme.is_default:
        session.execute(
            update(PointsScheme)
            .where(
                PointsScheme.league_id == league_id,
                _season_predicate(season_id),
                PointsScheme.id != scheme.id,
            )
            .values(is_default=False)
        )

    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=league_id,
        entity="points_scheme",
        entity_id=str(scheme.id),
        action="create",
        before=None,
        after=_scheme_state(scheme),
    )

    session.commit()
    session.refresh(scheme)
    return _scheme_to_read(scheme)


@router.patch("/points-schemes/{scheme_id}", response_model=PointsSchemeRead)
async def update_points_scheme(
    scheme_id: UUID,
    payload: PointsSchemeUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> PointsSchemeRead:
    scheme = (
        session.execute(
            select(PointsScheme)
            .options(joinedload(PointsScheme.rules))
            .where(PointsScheme.id == scheme_id)
        )
        .scalars()
        .first()
    )
    if scheme is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="POINTS_SCHEME_NOT_FOUND",
            message="Points scheme not found",
        )

    membership = require_membership(session, league_id=scheme.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    before_state = _scheme_state(scheme)
    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        new_name = update_data["name"].strip()
        if not new_name:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_NAME",
                message="Points scheme name is required",
                field="name",
            )
        scheme.name = new_name

    if "season_id" in update_data:
        season_id = _ensure_season(
            session, league_id=scheme.league_id, season_id=update_data["season_id"]
        )
        scheme.season_id = season_id

    if "rules" in update_data and update_data["rules"] is not None:
        entries = _validate_rules(update_data["rules"])
        _set_rules_for_scheme(scheme, entries)

    if "is_default" in update_data and update_data["is_default"] is not None:
        make_default = bool(update_data["is_default"])
        if make_default:
            session.execute(
                update(PointsScheme)
                .where(
                    PointsScheme.league_id == scheme.league_id,
                    _season_predicate(scheme.season_id),
                    PointsScheme.id != scheme.id,
                )
                .values(is_default=False)
            )
            scheme.is_default = True
        else:
            other_defaults = (
                session.execute(
                    select(PointsScheme).where(
                        PointsScheme.league_id == scheme.league_id,
                        _season_predicate(scheme.season_id),
                        PointsScheme.id != scheme.id,
                        PointsScheme.is_default.is_(True),
                    )
                )
                .scalars()
                .all()
            )
            if not other_defaults:
                raise api_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="MISSING_DEFAULT_SCHEME",
                    message="At least one default scheme is required per season",
                )
            scheme.is_default = False

    after_state = _scheme_state(scheme)
    if before_state != after_state:
        record_audit_log(
            session,
            actor_id=current_user.id,
            league_id=scheme.league_id,
            entity="points_scheme",
            entity_id=str(scheme.id),
            action="update",
            before=before_state,
            after=after_state,
        )

    session.commit()
    session.refresh(scheme)
    return _scheme_to_read(scheme)


@router.delete("/points-schemes/{scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_points_scheme(
    scheme_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    scheme = (
        session.execute(
            select(PointsScheme)
            .options(joinedload(PointsScheme.rules))
            .where(PointsScheme.id == scheme_id)
        )
        .scalars()
        .first()
    )
    if scheme is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="POINTS_SCHEME_NOT_FOUND",
            message="Points scheme not found",
        )

    membership = require_membership(session, league_id=scheme.league_id, user_id=current_user.id)
    require_role_at_least(membership, minimum=LeagueRole.ADMIN)

    before_state = _scheme_state(scheme)

    if scheme.is_default:
        related_events = session.execute(
            select(Event.id).where(Event.season_id == scheme.season_id)
        ).first()
        if related_events is not None:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="SCHEME_IN_USE",
                message="Cannot delete default scheme while events exist for the season",
            )

        other_scheme_exists = session.execute(
            select(PointsScheme.id).where(
                PointsScheme.league_id == scheme.league_id,
                PointsScheme.id != scheme.id,
            )
        ).first()
        if not other_scheme_exists:
            raise api_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="MISSING_DEFAULT_SCHEME",
                message="At least one points scheme must remain",
            )

    session.delete(scheme)
    record_audit_log(
        session,
        actor_id=current_user.id,
        league_id=scheme.league_id,
        entity="points_scheme",
        entity_id=str(scheme.id),
        action="delete",
        before=before_state,
        after=None,
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
