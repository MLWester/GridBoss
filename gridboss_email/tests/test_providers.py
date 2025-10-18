from __future__ import annotations

import httpx
import pytest

from gridboss_email.errors import EmailDeliveryError
from gridboss_email.models import EmailContent
from gridboss_email.providers import (
    SendGridProvider,
    get_email_provider,
)


def _sample_content(**overrides: str) -> EmailContent:
    base = {
        "recipient": "driver@example.com",
        "subject": "Welcome to GridBoss",
        "html_body": "<p>Hello Racer!</p>",
        "text_body": "Hello Racer!",
        "from_email": "notifications@example.com",
    }
    base.update(overrides)
    return EmailContent(**base)  # type: ignore[arg-type]


def test_sendgrid_provider_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        status_code = 202
        text = "Accepted"

    def fake_post(url: str, *, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = SendGridProvider("sg-test-key")
    provider.send(_sample_content())

    assert captured["url"] == "https://api.sendgrid.com/v3/mail/send"
    headers = captured["headers"]
    assert headers and headers["Authorization"] == "Bearer sg-test-key"
    payload = captured["json"]
    assert payload["from"]["email"] == "notifications@example.com"
    assert payload["personalizations"][0]["to"][0]["email"] == "driver@example.com"
    assert payload["subject"] == "Welcome to GridBoss"
    assert {"type": "text/plain", "value": "Hello Racer!"} in payload["content"]
    assert {"type": "text/html", "value": "<p>Hello Racer!</p>"} in payload["content"]
    assert captured["timeout"] == 10


def test_sendgrid_provider_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(*args, **kwargs):
        raise httpx.RequestError("boom", request=httpx.Request("POST", "https://api.sendgrid.com"))

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = SendGridProvider("sg-test-key")

    with pytest.raises(EmailDeliveryError):
        provider.send(_sample_content())


def test_sendgrid_provider_non_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 429
        text = "rate limited"

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response())
    provider = SendGridProvider("sg-test-key")

    with pytest.raises(EmailDeliveryError):
        provider.send(_sample_content())


def test_get_email_provider_prefers_sendgrid() -> None:
    provider = get_email_provider(sendgrid_api_key="key", smtp_url="smtp://user:pass@host")
    assert isinstance(provider, SendGridProvider)


def test_get_email_provider_returns_none() -> None:
    provider = get_email_provider(sendgrid_api_key=None, smtp_url=None)
    assert provider is None
