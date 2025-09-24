from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import redis
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.db.models import Driver, Event, EventStatus, Result

logger = logging.getLogger("app.standings")


@dataclass
class StandingsCacheConfig:
    redis_url: str
    ttl_seconds: int = 300


class StandingsCache:
    def __init__(self, config: StandingsCacheConfig) -> None:
        self.config = config
        self._redis_client: redis.Redis | None = None
        self._memory_store: dict[str, tuple[str, float]] = {}
        try:
            self._redis_client = redis.Redis.from_url(config.redis_url, decode_responses=True)
            self._redis_client.ping()
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning(
                "Standings cache Redis connection failed: %s -- using in-memory cache", exc
            )
            self._redis_client = None

    def _build_key(self, league_id: UUID, season_id: UUID | None) -> str:
        season_part = str(season_id) if season_id is not None else "none"
        return f"standings:{league_id}:{season_part}".lower()

    def get(self, *, league_id: UUID, season_id: UUID | None) -> dict[str, Any] | None:
        key = self._build_key(league_id, season_id)
        raw_payload: str | None
        if self._redis_client is not None:
            try:
                raw_payload = self._redis_client.get(key)
            except redis.RedisError as exc:  # pragma: no cover - treat as cache miss
                logger.warning("Redis error fetching standings cache: %s", exc)
                raw_payload = None
        else:
            record = self._memory_store.get(key)
            if record is None:
                raw_payload = None
            else:
                cached_value, expires_at = record
                if expires_at < time.time():
                    self._memory_store.pop(key, None)
                    raw_payload = None
                else:
                    raw_payload = cached_value
        if raw_payload is None:
            return None
        try:
            return json.loads(raw_payload)
        except json.JSONDecodeError:
            logger.warning("Invalid standings cache payload for %s", key)
            self.invalidate(league_id=league_id, season_id=season_id)
            return None

    def set(self, *, league_id: UUID, season_id: UUID | None, payload: dict[str, Any]) -> None:
        key = self._build_key(league_id, season_id)
        raw_payload = json.dumps(payload)
        if self._redis_client is not None:
            try:
                self._redis_client.setex(key, self.config.ttl_seconds, raw_payload)
                return
            except redis.RedisError as exc:  # pragma: no cover - fallback to memory
                logger.warning("Redis error storing standings cache: %s", exc)
        expires_at = time.time() + self.config.ttl_seconds
        self._memory_store[key] = (raw_payload, expires_at)

    def invalidate(self, *, league_id: UUID, season_id: UUID | None) -> None:
        key = self._build_key(league_id, season_id)
        if self._redis_client is not None:
            try:
                self._redis_client.delete(key)
            except redis.RedisError as exc:  # pragma: no cover - log and continue
                logger.warning("Redis error deleting standings cache key %s: %s", key, exc)
        self._memory_store.pop(key, None)


def _sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    best_finish = item["best_finish"]
    best_finish_rank = best_finish if best_finish is not None else 1_000_000
    return (-item["points"], -item["wins"], best_finish_rank, item["display_name"].lower())


def calculate_standings(
    session: Session,
    *,
    league_id: UUID,
    season_id: UUID | None,
) -> list[dict[str, Any]]:
    event_filters = [
        Event.league_id == league_id,
        Event.status == EventStatus.COMPLETED.value,
    ]
    if season_id is None:
        event_filters.append(Event.season_id.is_(None))
    else:
        event_filters.append(Event.season_id == season_id)

    event_join = and_(Event.id == Result.event_id, *event_filters)

    points_expr = func.coalesce(
        func.sum(
            case((Event.id.isnot(None), Result.total_points), else_=0),
        ),
        0,
    ).label("points")
    wins_expr = func.coalesce(
        func.sum(
            case((and_(Event.id.isnot(None), Result.finish_position == 1), 1), else_=0),
        ),
        0,
    ).label("wins")
    best_finish_expr = func.min(
        case((Event.id.isnot(None), Result.finish_position))
    ).label("best_finish")

    stmt = (
        select(
            Driver.id.label("driver_id"),
            Driver.display_name.label("display_name"),
            points_expr,
            wins_expr,
            best_finish_expr,
        )
        .select_from(Driver)
        .join(Result, Result.driver_id == Driver.id, isouter=True)
        .join(Event, event_join, isouter=True)
        .where(Driver.league_id == league_id)
        .group_by(Driver.id, Driver.display_name)
    )

    rows = session.execute(stmt).all()

    standings: list[dict[str, Any]] = []
    for row in rows:
        points_value = int(row.points or 0)
        wins_value = int(row.wins or 0)
        best_finish_value = int(row.best_finish) if row.best_finish is not None else None
        standings.append(
            {
                "driver_id": row.driver_id,
                "display_name": row.display_name,
                "points": points_value,
                "wins": wins_value,
                "best_finish": best_finish_value,
            }
        )

    standings.sort(key=_sort_key)
    return standings


_cache_instance: StandingsCache | None = None


def get_standings_cache(config: StandingsCacheConfig) -> StandingsCache:
    global _cache_instance  # noqa: PLW0603 - cache singleton for reuse
    if (
        _cache_instance is None
        or _cache_instance.config.redis_url != config.redis_url
        or _cache_instance.config.ttl_seconds != config.ttl_seconds
    ):
        _cache_instance = StandingsCache(config)
    return _cache_instance
