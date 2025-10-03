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

    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_price_pro: str = Field(default="", alias="STRIPE_PRICE_PRO")
    stripe_price_elite: str = Field(default="", alias="STRIPE_PRICE_ELITE")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")

    discord_client_id: str = Field(alias="DISCORD_CLIENT_ID")
    discord_client_secret: str = Field(alias="DISCORD_CLIENT_SECRET")
    discord_redirect_uri: AnyHttpUrl = Field(alias="DISCORD_REDIRECT_URI")

    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_access_ttl_min: int = Field(default=15, alias="JWT_ACCESS_TTL_MIN")
    jwt_refresh_ttl_days: int = Field(default=14, alias="JWT_REFRESH_TTL_DAYS")

    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE")
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_exporter_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_ENDPOINT")
    otel_service_name: str = Field(default="gridboss-api", alias="OTEL_SERVICE_NAME")
    health_cache_seconds: int = Field(default=0, alias="HEALTH_CACHE_SECONDS")

    def cookie_secure(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
