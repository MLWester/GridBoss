from __future__ import annotations

import httpx

from app.core.settings import Settings

TOKEN_URL = "https://discord.com/api/oauth2/token"  # noqa: S105
USER_URL = "https://discord.com/api/users/@me"


class DiscordOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
    ) -> dict[str, str]:
        data = {
            "client_id": self.settings.discord_client_id,
            "client_secret": self.settings.discord_client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": str(self.settings.discord_redirect_uri),
            "code_verifier": code_verifier,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(TOKEN_URL, data=data, headers=headers)
            response.raise_for_status()
            return response.json()

    async def fetch_user(self, *, access_token: str) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(USER_URL, headers=headers)
            response.raise_for_status()
            return response.json()


def get_discord_client(settings: Settings) -> DiscordOAuthClient:
    return DiscordOAuthClient(settings)
