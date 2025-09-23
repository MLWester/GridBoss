from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_env: Literal["development", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    app_url: AnyHttpUrl = Field(default="http://localhost:5173", alias="APP_URL")
    api_url: AnyHttpUrl = Field(default="http://localhost:8000", alias="API_URL")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    discord_client_id: str = Field(alias="DISCORD_CLIENT_ID")
    discord_client_secret: str = Field(alias="DISCORD_CLIENT_SECRET")
    discord_redirect_uri: AnyHttpUrl = Field(alias="DISCORD_REDIRECT_URI")

    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_access_ttl_min: int = Field(default=15, alias="JWT_ACCESS_TTL_MIN")
    jwt_refresh_ttl_days: int = Field(default=14, alias="JWT_REFRESH_TTL_DAYS")

    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    def cookie_secure(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
