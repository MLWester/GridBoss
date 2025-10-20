from __future__ import annotations

from functools import lru_cache
from typing import Any, ClassVar, Literal

from pydantic import AnyHttpUrl, AnyUrl, Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration for all GridBoss services."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    app_env: Literal["development", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    app_url: AnyHttpUrl = Field(default="http://localhost:5173", alias="APP_URL")
    api_url: AnyHttpUrl = Field(default="http://localhost:8000", alias="API_URL")
    api_port: int = Field(default=8000, alias="API_PORT")
    admin_mode: bool = Field(default=False, alias="ADMIN_MODE")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    # Auth / security
    jwt_secret: str = Field(default="dev-jwt-secret", alias="JWT_SECRET")
    jwt_access_ttl_min: int = Field(default=15, alias="JWT_ACCESS_TTL_MIN")
    jwt_refresh_ttl_days: int = Field(default=14, alias="JWT_REFRESH_TTL_DAYS")

    # Data stores
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/gridboss",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Discord integration
    discord_client_id: str = Field(
        default="111111111111111111", alias="DISCORD_CLIENT_ID"
    )
    discord_client_secret: str = Field(
        default="dev-discord-secret", alias="DISCORD_CLIENT_SECRET"
    )
    discord_redirect_uri: AnyHttpUrl = Field(
        default="http://localhost:8000/auth/discord/callback",
        alias="DISCORD_REDIRECT_URI",
    )
    discord_bot_token: str = Field(default="dev-bot-token", alias="DISCORD_BOT_TOKEN")
    discord_link_path: str = Field(
        default="/settings/discord", alias="DISCORD_LINK_PATH"
    )

    # Stripe billing
    stripe_secret_key: str = Field(
        default="sk_test_placeholder", alias="STRIPE_SECRET_KEY"
    )
    stripe_price_pro: str = Field(default="price_dev_pro", alias="STRIPE_PRICE_PRO")
    stripe_price_elite: str = Field(
        default="price_dev_elite", alias="STRIPE_PRICE_ELITE"
    )
    stripe_webhook_secret: str = Field(
        default="whsec_dev", alias="STRIPE_WEBHOOK_SECRET"
    )
    stripe_webhook_forward: AnyUrl | None = Field(
        default=None, alias="STRIPE_WEBHOOK_FORWARD"
    )

    # Analytics / telemetry
    analytics_enabled: bool = Field(default=False, alias="ANALYTICS_ENABLED")
    analytics_salt: str | None = Field(default=None, alias="ANALYTICS_SALT")

    sentry_dsn: AnyUrl | None = Field(default=None, alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(
        default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE"
    )
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_exporter_endpoint: AnyUrl | None = Field(
        default=None, alias="OTEL_EXPORTER_ENDPOINT"
    )
    otel_service_name: str = Field(default="gridboss-api", alias="OTEL_SERVICE_NAME")
    health_cache_seconds: int = Field(default=0, alias="HEALTH_CACHE_SECONDS")

    # Email
    email_enabled: bool = Field(default=False, alias="EMAIL_ENABLED")
    smtp_url: AnyUrl | None = Field(default=None, alias="SMTP_URL")
    sendgrid_api_key: str | None = Field(default=None, alias="SENDGRID_API_KEY")
    email_from_address: str | None = Field(default=None, alias="EMAIL_FROM_ADDRESS")

    # Object storage
    s3_enabled: bool = Field(default=False, alias="S3_ENABLED")
    s3_endpoint: AnyUrl | None = Field(default=None, alias="S3_ENDPOINT")
    s3_region: str | None = Field(default=None, alias="S3_REGION")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_access_key: str | None = Field(default=None, alias="S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, alias="S3_SECRET_KEY")
    s3_presign_ttl: int | None = Field(default=3600, alias="S3_PRESIGN_TTL")

    # Worker
    worker_threads: int = Field(default=8, alias="WORKER_THREADS")
    worker_name: str = Field(default="gridboss-worker", alias="WORKER_NAME")
    worker_retry_min_backoff_ms: int = Field(
        default=1_000, alias="WORKER_RETRY_MIN_BACKOFF_MS"
    )
    worker_retry_max_backoff_ms: int = Field(
        default=300_000, alias="WORKER_RETRY_MAX_BACKOFF_MS"
    )
    worker_retry_max_retries: int = Field(default=5, alias="WORKER_RETRY_MAX_RETRIES")

    @field_validator(
        "sentry_dsn",
        "otel_exporter_endpoint",
        "smtp_url",
        "stripe_webhook_forward",
        "s3_endpoint",
        mode="before",
    )
    @classmethod
    def _empty_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    REQUIRED_NON_EMPTY_FIELDS: ClassVar[tuple[str, ...]] = (
        "jwt_secret",
        "database_url",
        "redis_url",
        "discord_client_id",
        "discord_client_secret",
        "discord_redirect_uri",
        "discord_bot_token",
        "stripe_secret_key",
        "stripe_price_pro",
        "stripe_price_elite",
        "stripe_webhook_secret",
    )

    PRODUCTION_OVERRIDES: ClassVar[dict[str, Any]] = {
        "jwt_secret": "dev-jwt-secret",
        "discord_client_secret": "dev-discord-secret",
        "discord_bot_token": "dev-bot-token",
        "stripe_secret_key": "sk_test_placeholder",
        "stripe_price_pro": "price_dev_pro",
        "stripe_price_elite": "price_dev_elite",
        "stripe_webhook_secret": "whsec_dev",
    }

    @model_validator(mode="after")
    def _validate_required_settings(self) -> Settings:
        missing: list[str] = []
        for field_name in self.REQUIRED_NON_EMPTY_FIELDS:
            value = getattr(self, field_name)
            if isinstance(value, str):
                if not value.strip():
                    missing.append(field_name)
            elif value is None:
                missing.append(field_name)

        if missing:
            raise ValueError(f"Missing required settings: {', '.join(sorted(missing))}")

        if self.app_env == "production":
            production_issues: list[str] = []
            for field_name, sentinel in self.PRODUCTION_OVERRIDES.items():
                if getattr(self, field_name) == sentinel:
                    production_issues.append(field_name)
            if production_issues:
                raise ValueError(
                    "Production environment requires real credentials for: "
                    + ", ".join(sorted(production_issues))
                )

        if self.analytics_enabled and not self.analytics_salt:
            raise ValueError(
                "ANALYTICS_ENABLED requires ANALYTICS_SALT to be configured."
            )

        if self.email_enabled and not (self.smtp_url or self.sendgrid_api_key):
            raise ValueError(
                "EMAIL_ENABLED requires SMTP_URL or SENDGRID_API_KEY to be provided."
            )

        if self.s3_enabled:
            required_s3_fields = (
                "s3_endpoint",
                "s3_bucket",
                "s3_access_key",
                "s3_secret_key",
            )
            missing_s3 = [
                name for name in required_s3_fields if not getattr(self, name)
            ]
            if missing_s3:
                raise ValueError(
                    "S3_ENABLED requires full S3 configuration: "
                    + ", ".join(sorted(missing_s3))
                )
            if self.s3_presign_ttl is not None and self.s3_presign_ttl <= 0:
                raise ValueError("S3_PRESIGN_TTL must be a positive integer when S3 is enabled.")

        return self

    def cookie_secure(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
