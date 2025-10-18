from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EmailEnvelope:
    """Payload passed from the API to the worker for email delivery."""

    message_id: str
    template_id: str
    recipient: str
    context: dict[str, Any] = field(default_factory=dict)
    locale: str = "en"
    league_id: str | None = None
    actor_id: str | None = None
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "template_id": self.template_id,
            "recipient": self.recipient,
            "context": self.context,
            "locale": self.locale,
            "league_id": self.league_id,
            "actor_id": self.actor_id,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailEnvelope:
        return cls(
            message_id=data["message_id"],
            template_id=data["template_id"],
            recipient=data["recipient"],
            context=dict(data.get("context") or {}),
            locale=data.get("locale", "en"),
            league_id=data.get("league_id"),
            actor_id=data.get("actor_id"),
            request_id=data.get("request_id"),
        )


@dataclass(frozen=True)
class EmailTemplate:
    """Template definition loaded from disk."""

    subject: str
    html_body: str
    text_body: str


@dataclass(frozen=True)
class EmailContent:
    """Materialised email content ready for delivery."""

    recipient: str
    subject: str
    html_body: str
    text_body: str
    from_email: str
