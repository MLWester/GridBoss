from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from gridboss_config import Settings, get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_email_requires_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    monkeypatch.delenv("SMTP_URL", raising=False)
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    _reset_settings_cache()
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "EMAIL_ENABLED requires SMTP_URL or SENDGRID_API_KEY" in str(exc.value)
    monkeypatch.setenv("EMAIL_ENABLED", "false")
    _reset_settings_cache()


def test_s3_requires_full_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.local")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    _reset_settings_cache()
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "S3_ENABLED requires full S3 configuration" in str(exc.value)
    monkeypatch.setenv("S3_ENABLED", "false")
    for key in ("S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY", "S3_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)
    _reset_settings_cache()


def test_production_requires_real_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
    _reset_settings_cache()
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "Production environment requires real credentials" in str(exc.value)
    # Restore defaults for other tests
    monkeypatch.setenv("APP_ENV", "test")
    os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
    _reset_settings_cache()
