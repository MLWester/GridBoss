from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DiscordLinkRequest(BaseModel):
    guild_id: str = Field(min_length=1)
    channel_id: str = Field(min_length=1)


class DiscordIntegrationRead(BaseModel):
    id: UUID
    league_id: UUID
    guild_id: str
    channel_id: str | None
    installed_by_user: UUID | None
    is_active: bool

    class Config:
        from_attributes = True
