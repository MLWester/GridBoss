from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class BotConfig:
    token: str
    app_url: str
    link_path: str = "/settings/discord"


def load_config() -> BotConfig:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    app_url = os.getenv("APP_URL", "http://localhost:5173")
    link_path = os.getenv("DISCORD_LINK_PATH", "/settings/discord")

    return BotConfig(token=token, app_url=app_url.rstrip("/"), link_path=link_path)
