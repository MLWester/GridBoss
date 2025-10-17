from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from .errors import EmailConfigurationError, EmailDeliveryError
from .models import EmailContent


class EmailProvider(Protocol):
    name: str

    def send(self, message: EmailContent) -> None:  # pragma: no cover - protocol
        ...


class SendGridProvider:
    name = "sendgrid"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def send(self, message: EmailContent) -> None:
        payload = {
            "from": {"email": message.from_email},
            "personalizations": [
                {
                    "to": [{"email": message.recipient}],
                }
            ],
            "subject": message.subject,
            "content": [],
        }
        if message.text_body:
            payload["content"].append({"type": "text/plain", "value": message.text_body})
        if message.html_body:
            payload["content"].append({"type": "text/html", "value": message.html_body})

        try:
            response = httpx.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=10,
            )
        except httpx.HTTPError as exc:
            raise EmailDeliveryError(f"SendGrid request failed: {exc}") from exc

        if response.status_code >= 300:
            raise EmailDeliveryError(
                f"SendGrid responded with {response.status_code}: {response.text}"
            )


class SMTPProvider:
    name = "smtp"

    def __init__(self, smtp_url: str) -> None:
        self._smtp_url = smtp_url

    def send(self, message: EmailContent) -> None:
        parsed = urlparse(self._smtp_url)
        if parsed.scheme not in {"smtp", "smtps"}:
            raise EmailConfigurationError("SMTP_URL must use smtp:// or smtps:// scheme")
        host = parsed.hostname or ""
        port = parsed.port or (465 if parsed.scheme == "smtps" else 25)
        username = unquote(parsed.username) if parsed.username else None
        password = unquote(parsed.password) if parsed.password else None
        query = parse_qs(parsed.query)
        use_starttls = parsed.scheme == "smtp" and query.get("starttls", ["0"])[0] in {"1", "true"}

        msg = EmailMessage()
        msg["From"] = message.from_email
        msg["To"] = message.recipient
        msg["Subject"] = message.subject

        if message.html_body:
            msg.set_content(message.text_body or "")
            msg.add_alternative(message.html_body, subtype="html")
        else:
            msg.set_content(message.text_body or "")

        try:
            if parsed.scheme == "smtps":
                with smtplib.SMTP_SSL(host=host, port=port, timeout=10) as smtp:
                    if username and password:
                        smtp.login(username, password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(host=host, port=port, timeout=10) as smtp:
                    if use_starttls:
                        smtp.starttls()
                    if username and password:
                        smtp.login(username, password)
                    smtp.send_message(msg)
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError(f"SMTP send failed: {exc}") from exc


def get_email_provider(
    *, sendgrid_api_key: str | None, smtp_url: str | None
) -> EmailProvider | None:
    if sendgrid_api_key:
        return SendGridProvider(sendgrid_api_key)
    if smtp_url:
        return SMTPProvider(smtp_url)
    return None
