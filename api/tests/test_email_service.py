from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.db.models import AuditLog
from app.db import session as db_session
from app.services import email as email_service
from app.core.settings import get_settings


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


@pytest.fixture(autouse=True)
def reset_database(monkeypatch: pytest.MonkeyPatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    email_service.email_jobs = None  # type: ignore[assignment]
    db_session._engine = engine  # type: ignore[attr-defined]
    db_session.SessionLocal = TestingSessionLocal  # type: ignore[attr-defined]
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "notifications@example.com")
    monkeypatch.setenv("EMAIL_ENABLED", "false")
    monkeypatch.setenv("SENDGRID_API_KEY", "")
    monkeypatch.setenv("SMTP_URL", "")
    get_settings.cache_clear()


def _fetch_logs() -> list[AuditLog]:
    session: Session = TestingSessionLocal()
    try:
        return session.execute(select(AuditLog)).scalars().all()
    finally:
        session.close()


def test_queue_email_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_ENABLED", "false")
    get_settings.cache_clear()

    called: list[dict[str, object]] = []
    email_service.email_jobs = SimpleNamespace(  # type: ignore[assignment]
        send_transactional_email=SimpleNamespace(send=lambda payload: called.append(payload))
    )

    email_service.queue_transactional_email(
        template_id="welcome",
        recipient="driver@example.com",
        context={"display_name": "Driver", "app_url": "http://localhost"},
    )

    logs = _fetch_logs()
    assert logs and logs[0].action == "email_disabled"
    assert not called


def test_queue_email_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    monkeypatch.setenv("SENDGRID_API_KEY", "test-key")
    get_settings.cache_clear()

    captured: list[dict[str, object]] = []

    email_service.email_jobs = SimpleNamespace(  # type: ignore[assignment]
        send_transactional_email=SimpleNamespace(send=lambda payload: captured.append(payload))
    )

    email_service.queue_transactional_email(
        template_id="welcome",
        recipient="driver@example.com",
        context={"display_name": "Driver", "app_url": "http://localhost"},
    )

    logs = _fetch_logs()
    assert logs and logs[0].action == "email_queued"
    assert captured and captured[0]["recipient"] == "driver@example.com"


def test_queue_email_worker_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    monkeypatch.setenv("SENDGRID_API_KEY", "test-key")
    get_settings.cache_clear()

    email_service.email_jobs = None  # type: ignore[assignment]

    email_service.queue_transactional_email(
        template_id="welcome",
        recipient="driver@example.com",
        context={"display_name": "Driver", "app_url": "http://localhost"},
    )

    logs = _fetch_logs()
    assert logs and logs[0].action == "email_worker_unavailable"
