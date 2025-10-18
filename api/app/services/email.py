from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from app.core.observability import get_request_id
from app.core.settings import get_settings
from app.db.session import get_sessionmaker
from app.services.audit import record_audit_log
from gridboss_email import EmailEnvelope

logger = logging.getLogger("app.services.email")

DEFAULT_LOCALE = "en"

try:
    from worker.jobs import email as email_jobs
except Exception:  # pragma: no cover - worker optional during testing
    email_jobs = None  # type: ignore


def _audit_session():
    session_factory = get_sessionmaker()
    return session_factory()


def _to_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except (ValueError, TypeError):
        logger.debug("Unable to coerce value into UUID: %s", value)
        return None


def queue_transactional_email(
    *,
    template_id: str,
    recipient: str,
    context: dict[str, Any],
    locale: str | None = None,
    league_id: str | None = None,
    actor_id: str | None = None,
) -> str:
    """Queue an email for asynchronous delivery."""
    settings = get_settings()
    message_id = str(uuid4())
    resolved_locale = locale or DEFAULT_LOCALE

    status = "queued"
    reason: str | None = None

    if not recipient:
        logger.debug("Skipping transactional email because recipient is empty (template=%s)", template_id)
        status = "invalid_recipient"
    elif not settings.email_enabled:
        logger.info("Email disabled; skipping delivery for template %s", template_id)
        status = "disabled"
    elif email_jobs is None or not hasattr(email_jobs, "send_transactional_email"):
        logger.warning("Email worker not available; cannot queue template %s", template_id)
        status = "worker_unavailable"
        reason = "worker_unavailable"
    else:
        envelope = EmailEnvelope(
            message_id=message_id,
            template_id=template_id,
            recipient=recipient,
            context=context,
            locale=resolved_locale,
            league_id=league_id,
            actor_id=actor_id,
            request_id=get_request_id(),
        )
        try:
            email_jobs.send_transactional_email.send(envelope.to_dict())
        except Exception as exc:  # pragma: no cover - network failure to broker
            logger.exception("Failed to enqueue transactional email: %s", exc)
            status = "queue_failed"
            reason = "enqueue_error"

    session = _audit_session()
    try:
        record_audit_log(
            session,
            actor_id=_to_uuid(actor_id),
            league_id=_to_uuid(league_id),
            entity="email",
            entity_id=message_id,
            action="email_" + status,
            before=None,
            after={
                "recipient": recipient,
                "template": template_id,
                "status": status,
                "locale": resolved_locale,
                **({"reason": reason} if reason else {}),
            },
        )
        session.commit()
    except Exception:  # pragma: no cover - logging should not break flow
        session.rollback()
        logger.exception("Failed to record audit log for email %s", message_id)
    finally:
        session.close()

    return message_id


__all__ = ["queue_transactional_email"]
