from __future__ import annotations

import logging
from uuid import UUID

import dramatiq

from app.core.observability import bind_request_id, clear_context
from app.core.settings import get_settings
from app.db.session import get_sessionmaker
from app.services.audit import record_audit_log
from gridboss_email import (
    EmailConfigurationError,
    EmailDeliveryError,
    EmailEnvelope,
    render_email_content,
)
from gridboss_email.providers import get_email_provider

logger = logging.getLogger("worker.jobs.email")

SessionLocal = get_sessionmaker()


def _to_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except (ValueError, TypeError):
        logger.debug("Invalid UUID value encountered in email job metadata: %s", value)
        return None


def _record_status(
    session,
    *,
    envelope: EmailEnvelope,
    status: str,
    provider: str | None = None,
    detail: str | None = None,
) -> None:
    after_state: dict[str, str] = {
        "recipient": envelope.recipient,
        "template": envelope.template_id,
        "status": status,
    }
    if provider:
        after_state["provider"] = provider
    if detail:
        after_state["detail"] = detail

    record_audit_log(
        session,
        actor_id=_to_uuid(envelope.actor_id),
        league_id=_to_uuid(envelope.league_id),
        entity="email",
        entity_id=envelope.message_id,
        action="email_" + status,
        before=None,
        after=after_state,
    )


@dramatiq.actor(max_retries=3)
def send_transactional_email(payload: dict[str, object]) -> None:
    envelope = EmailEnvelope.from_dict(payload)
    settings = get_settings()
    session = SessionLocal()

    bind_request_id(envelope.request_id)

    try:
        provider = get_email_provider(
            sendgrid_api_key=settings.sendgrid_api_key,
            smtp_url=settings.smtp_url,
        )
        if provider is None:
            logger.error("No email provider configured; cannot deliver template %s", envelope.template_id)
            _record_status(
                session,
                envelope=envelope,
                status="failed",
                detail="no_provider",
            )
            session.commit()
            return

        if not settings.email_from_address:
            raise EmailConfigurationError("EMAIL_FROM_ADDRESS must be configured")

        content = render_email_content(envelope, from_email=settings.email_from_address)
        provider.send(content)

        _record_status(
            session,
            envelope=envelope,
            status="sent",
            provider=provider.name,
        )
        session.commit()
    except EmailConfigurationError as exc:
        session.rollback()
        logger.error("Email configuration error: %s", exc)
        session.begin()
        _record_status(
            session,
            envelope=envelope,
            status="failed",
            detail="configuration_error",
        )
        session.commit()
    except EmailDeliveryError as exc:
        session.rollback()
        logger.warning(
            "Email delivery failed for template %s: %s",
            envelope.template_id,
            exc,
        )
        session.begin()
        _record_status(
            session,
            envelope=envelope,
            status="failed",
            detail="delivery_error",
        )
        session.commit()
        raise
    except Exception:
        session.rollback()
        logger.exception("Unexpected error delivering email %s", envelope.message_id)
        session.begin()
        _record_status(
            session,
            envelope=envelope,
            status="failed",
            detail="unexpected_error",
        )
        session.commit()
        raise
    finally:
        session.close()
        clear_context()


__all__ = ["send_transactional_email"]
