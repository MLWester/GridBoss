from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the worker package is importable when tests run from the API directory.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

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
    config = load_config()
    assert config.redis_url == "redis://localhost:6379/0"
    assert config.worker_threads == 8
    assert config.retry_max_retries == 5
