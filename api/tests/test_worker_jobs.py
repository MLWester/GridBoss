from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the worker package is importable when tests run from the API directory.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from gridboss_config import get_settings
from worker.config import load_config
from worker.jobs import heartbeat


def test_heartbeat_logs_message(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO"):
        heartbeat.fn(message="ping", context="pytest")
    assert "Heartbeat: ping" in caplog.text
    assert "pytest" in caplog.text


def test_load_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("WORKER_THREADS", raising=False)
    get_settings.cache_clear()  # type: ignore[attr-defined]
    config = load_config()
    settings = get_settings()
    assert config.redis_url == settings.redis_url
    assert config.worker_threads == settings.worker_threads
    assert config.retry_max_retries == settings.worker_retry_max_retries
