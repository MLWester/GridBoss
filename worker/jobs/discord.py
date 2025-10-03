from __future__ import annotations

import logging
import uuid

import dramatiq
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models import DiscordIntegration, Event, League, Result
from app.db.session import get_sessionmaker
from app.services.audit import record_audit_log
from worker.services.discord import (
    DiscordConfigurationError,
    DiscordMessage,
    DiscordNotifier,
    DiscordPermissionError,
    DiscordRateLimitError,
    build_results_embed,
    create_notifier_from_env,
)

logger = logging.getLogger("worker.jobs.discord")

SessionLocal = get_sessionmaker()


def _session():
    return SessionLocal()


def _get_notifier() -> DiscordNotifier | None:
    try:
        return create_notifier_from_env()
    except DiscordConfigurationError as exc:
        logger.error("Discord notifier configuration error: %s", exc)
        return None


def _record_failure(session, integration: DiscordIntegration, *, reason: str) -> None:
    before_state = {
        "is_active": integration.is_active,
        "channel_id": integration.channel_id,
        "guild_id": integration.guild_id,
    }
    integration.is_active = False
    record_audit_log(
        session,
        actor_id=None,
        league_id=integration.league_id,
        entity="discord_integration",
        entity_id=str(integration.id),
        action="discord_deactivated",
        before=before_state,
        after={**before_state, "is_active": False, "reason": reason},
    )


def _build_results_payload(session, event: Event) -> dict[str, str | list[dict[str, object]]]:
    league = session.get(League, event.league_id)
    season_name = None
    if event.season_id:
        season = event.season
        if season is not None:
            season_name = season.name
    results = (
        session.execute(
            select(Result)
            .options(joinedload(Result.driver))
            .where(Result.event_id == event.id)
            .order_by(Result.finish_position)
        )
        .scalars()
        .all()
    )
    entries = [
        {
            "driver": result.driver.display_name if result.driver else "Unknown",
            "points": result.total_points,
            "status": result.status,
        }
        for result in results
    ]
    embed = build_results_embed(
        event_name=event.name,
        league_name=league.name if league else "League",
        season_name=season_name,
        results=entries,
    )
    return {"embeds": [embed]}


@dramatiq.actor(max_retries=5)
def send_test_message(league_id: str, guild_id: str, channel_id: str) -> None:
    notifier = _get_notifier()
    if notifier is None:
        logger.warning("Skipping Discord test message because notifier is not configured")
        return

    session = _session()
    try:
        integration = (
            session.execute(
                select(DiscordIntegration).where(DiscordIntegration.league_id == uuid.UUID(league_id))
            )
            .scalars()
            .first()
        )
        if integration is None:
            logger.info("No Discord integration for league %s", league_id)
            return
        if not integration.is_active:
            logger.info("Discord integration inactive for league %s", league_id)
            return

        message = DiscordMessage(content="Test message queued! GridBoss bot is connected and ready.")
        notifier.send(channel_id, message)
        logger.info("Discord test message dispatched (league=%s, channel=%s)", league_id, channel_id)
    except DiscordRateLimitError:
        session.rollback()
        raise
    except DiscordPermissionError as exc:
        session.rollback()
        logger.error("Discord test message failed: %s", exc, extra={"league": league_id, "channel": channel_id})
        session.begin()
        refreshed = session.execute(
            select(DiscordIntegration).where(DiscordIntegration.league_id == uuid.UUID(league_id))
        ).scalars().first()
        if refreshed is not None:
            _record_failure(session, refreshed, reason="permission_error")
        session.commit()
        raise
    except Exception:  # pragma: no cover - unexpected errors
        session.rollback()
        raise
    else:
        session.commit()
    finally:
        session.close()


@dramatiq.actor(max_retries=5)
def announce_results(league_id: str, event_id: str) -> None:
    notifier = _get_notifier()
    if notifier is None:
        logger.warning("Skipping results announcement because notifier is not configured")
        return

    session = _session()
    try:
        integration = (
            session.execute(
                select(DiscordIntegration)
                .options(joinedload(DiscordIntegration.league))
                .where(DiscordIntegration.league_id == uuid.UUID(league_id))
            )
            .scalars()
            .first()
        )
        if integration is None or not integration.channel_id:
            logger.info("No Discord channel configured for league %s", league_id)
            return
        if not integration.is_active:
            logger.info("Discord integration inactive for league %s", league_id)
            return

        event = (
            session.execute(
                select(Event)
                .options(joinedload(Event.season))
                .where(Event.id == uuid.UUID(event_id))
            )
            .scalars()
            .first()
        )
        if event is None:
            logger.warning("Event %s not found for Discord announcement", event_id)
            return

        payload = _build_results_payload(session, event)
        message = DiscordMessage(content=None, embeds=payload["embeds"])
        notifier.send(integration.channel_id, message)
        logger.info(
            "Discord results announcement delivered (league=%s, event=%s)", league_id, event_id
        )
    except DiscordRateLimitError:
        session.rollback()
        raise
    except DiscordPermissionError as exc:
        session.rollback()
        logger.error(
            "Discord results announcement failed: %s",
            exc,
            extra={"league": league_id, "event": event_id},
        )
        session.begin()
        refreshed = session.execute(
            select(DiscordIntegration).where(DiscordIntegration.league_id == uuid.UUID(league_id))
        ).scalars().first()
        if refreshed is not None:
            _record_failure(session, refreshed, reason="permission_error")
        session.commit()
        raise
    except Exception:  # pragma: no cover - unexpected
        session.rollback()
        raise
    else:
        session.commit()
    finally:
        session.close()


__all__ = ["send_test_message", "announce_results"]
