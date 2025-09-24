from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Iterable

import httpx

logger = logging.getLogger("worker.discord")

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordRateLimitError(RuntimeError):
    """Raised when Discord responds with a rate limit."""


class DiscordPermissionError(RuntimeError):
    """Raised when the bot lacks permission to post to the configured channel."""


class DiscordConfigurationError(RuntimeError):
    """Raised when the bot is missing required configuration."""


@dataclass(frozen=True)
class DiscordMessage:
    content: str | None = None
    embeds: list[dict[str, Any]] | None = None


class DiscordNotifier:
    """Thin HTTP client wrapper for posting messages to Discord channels."""

    def __init__(self, bot_token: str, *, timeout: float = 10.0) -> None:
        if not bot_token:
            raise DiscordConfigurationError("DISCORD_BOT_TOKEN is not configured")
        self._bot_token = bot_token
        self._timeout = timeout

    def send(self, channel_id: str, message: DiscordMessage) -> None:
        payload: dict[str, Any] = {}
        if message.content:
            payload["content"] = message.content
        if message.embeds:
            payload["embeds"] = message.embeds

        headers = {
            "Authorization": f"Bot {self._bot_token}",
            "Content-Type": "application/json",
        }

        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After") or response.json().get("retry_after")
            logger.warning("Discord rate limit encountered", extra={"channel_id": channel_id, "retry_after": retry_after})
            raise DiscordRateLimitError(f"Rate limited posting to channel {channel_id}")

        if response.status_code in {401, 403, 404}:
            logger.error(
                "Discord permission failure",
                extra={"channel_id": channel_id, "payload": _safe_json(payload), "status": response.status_code},
            )
            raise DiscordPermissionError(f"Bot lacks permission for channel {channel_id}")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - unexpected HTTP errors
            logger.error(
                "Discord API error",
                extra={"channel_id": channel_id, "status": response.status_code, "body": response.text},
            )
            raise DiscordPermissionError("Discord API returned an error") from exc


def _safe_json(payload: dict[str, Any]) -> str:
    try:
        return json.dumps(payload)
    except TypeError:  # pragma: no cover - payload should be serialisable
        return "<unserializable payload>"


def create_notifier_from_env() -> DiscordNotifier:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    return DiscordNotifier(token)


def build_results_embed(
    *,
    event_name: str,
    league_name: str,
    season_name: str | None,
    results: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    lines = []
    for index, item in enumerate(results, start=1):
        podium_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, "•")
        driver_name = item.get("driver")
        points = item.get("points", 0)
        status = item.get("status", "FINISHED")
        line = f"{podium_emoji} **{driver_name}** — {points} pts ({status})"
        lines.append(line)

    description = "\n".join(lines) if lines else "No classified finishers."

    embed = {
        "title": f"{event_name} — Results",
        "description": description,
        "color": 0x5865F2,  # Discord blurple
        "footer": {
            "text": f"League: {league_name}" + (f" • Season: {season_name}" if season_name else "")
        },
    }
    return embed


__all__ = [
    "DiscordNotifier",
    "DiscordMessage",
    "DiscordRateLimitError",
    "DiscordPermissionError",
    "DiscordConfigurationError",
    "create_notifier_from_env",
    "build_results_embed",
]
