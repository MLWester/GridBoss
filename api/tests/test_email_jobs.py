from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.db.models import AuditLog
from app.db import session as db_session
from app.core.settings import get_settings
from gridboss_email.errors import EmailDeliveryError
from gridboss_email.models import EmailEnvelope
from worker.jobs import email as email_jobs


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

db_session._engine = engine  # type: ignore[attr-defined]
db_session.SessionLocal = TestingSessionLocal  # type: ignore[attr-defined]
email_jobs.SessionLocal = TestingSessionLocal  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def reset_database(monkeypatch: pytest.MonkeyPatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "notifications@example.com")
    monkeypatch.setenv("SENDGRID_API_KEY", "test-key")
    monkeypatch.setenv("SMTP_URL", "")
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    get_settings.cache_clear()


def _latest_audit() -> AuditLog | None:
    session: Session = TestingSessionLocal()
    try:
        return session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc())
        ).scalars().first()
    finally:
        session.close()


def test_email_job_success(monkeypatch: pytest.MonkeyPatch) -> None:
    sent_payload: list[object] = []

    class StubProvider:
        name = "stub"

        def send(self, content) -> None:  # type: ignore[no-untyped-def]
            sent_payload.append(content)

    monkeypatch.setattr(email_jobs, "get_email_provider", lambda **_: StubProvider())

    envelope = EmailEnvelope(
        message_id=str(uuid.uuid4()),
        template_id="welcome",
        recipient="driver@example.com",
        context={"display_name": "Driver", "app_url": "http://localhost"},
    )

    email_jobs.send_transactional_email.fn(envelope.to_dict())

    audit = _latest_audit()
    assert audit is not None
    assert audit.action == "email_sent"
    assert sent_payload, "provider should send exactly one message"


def test_email_job_delivery_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingProvider:
        name = "stub"

        def send(self, content) -> None:  # type: ignore[no-untyped-def]
            raise EmailDeliveryError("boom")

    monkeypatch.setattr(email_jobs, "get_email_provider", lambda **_: FailingProvider())

    envelope = EmailEnvelope(
        message_id=str(uuid.uuid4()),
        template_id="welcome",
        recipient="driver@example.com",
        context={"display_name": "Driver", "app_url": "http://localhost"},
    )

    with pytest.raises(EmailDeliveryError):
        email_jobs.send_transactional_email.fn(envelope.to_dict())

    audit = _latest_audit()
    assert audit is not None
    assert audit.action == "email_failed"


def test_email_job_no_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(email_jobs, "get_email_provider", lambda **_: None)

    envelope = EmailEnvelope(
        message_id=str(uuid.uuid4()),
        template_id="welcome",
        recipient="driver@example.com",
        context={"display_name": "Driver", "app_url": "http://localhost"},
    )

    email_jobs.send_transactional_email.fn(envelope.to_dict())

    audit = _latest_audit()
    assert audit is not None
    assert audit.action == "email_failed"
