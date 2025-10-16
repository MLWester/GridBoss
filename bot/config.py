from __future__ import annotations

from dataclasses import dataclass

from gridboss_config import get_settings


@dataclass(frozen=True)
class BotConfig:
    token: str
    app_url: str
    link_path: str = "/settings/discord"


def load_config() -> BotConfig:
    settings = get_settings()
    app_url = str(settings.app_url).rstrip("/")
    return BotConfig(
        token=settings.discord_bot_token.strip(),
        app_url=app_url,
        link_path=settings.discord_link_path,
    )
