# Configuration Reference

GridBoss services share a single configuration surface driven by environment variables. Values are loaded via `pydantic-settings` (see `gridboss_config/__init__.py`) and validated at start-up. The table below lists every supported key, its type, default value (used for development/test), and guidance for production deployments.

| Key | Type | Default (dev/test) | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | `development` \| `production` \| `test` | `development` | Controls feature toggles and cookie security. |
| `APP_URL` | URL | `http://localhost:5173` | Public URL of the frontend. Must not contain trailing slash in production. |
| `API_URL` | URL | `http://localhost:8000` | Base URL for the API service. |
| `API_PORT` | int | `8000` | Local port used by the API container/process. |
| `ADMIN_MODE` | bool | `false` | Enables founder-only admin console features. |
| `CORS_ORIGINS` | CSV string | `http://localhost:5173` | Comma-separated origins allowed by CORS middleware. |
| `JWT_SECRET` | string | `dev-jwt-secret` | **Required** â€“ change in production. Used to sign access/refresh tokens. |
| `JWT_ACCESS_TTL_MIN` | int | `15` | Access token lifetime in minutes. |
| `JWT_REFRESH_TTL_DAYS` | int | `14` | Refresh token lifetime in days. |
| `DATABASE_URL` | string | `postgresql+psycopg://postgres:postgres@localhost:5432/gridboss` | SQLAlchemy DSN for the primary database. |
| `REDIS_URL` | string | `redis://localhost:6379/0` | Redis connection URL used for cache, queues, and locks. |
| `WORKER_THREADS` | int | `8` | Number of Dramatiq worker threads. |
| `WORKER_NAME` | string | `gridboss-worker` | Identifier used for worker logging/metrics. |
| `WORKER_RETRY_MIN_BACKOFF_MS` | int | `1000` | Initial Dramatiq retry backoff in milliseconds. |
| `WORKER_RETRY_MAX_BACKOFF_MS` | int | `300000` | Maximum Dramatiq retry backoff in milliseconds. |
| `WORKER_RETRY_MAX_RETRIES` | int | `5` | Maximum retry attempts for Dramatiq jobs. |
| `DISCORD_CLIENT_ID` | string | `111111111111111111` | OAuth client ID. Replace with production app credentials. |
| `DISCORD_CLIENT_SECRET` | string | `dev-discord-secret` | OAuth client secret. **Required** in production. |
| `DISCORD_REDIRECT_URI` | URL | `http://localhost:8000/auth/discord/callback` | Discord OAuth redirect target. |
| `DISCORD_BOT_TOKEN` | string | `dev-bot-token` | Token used by the Discord bot/worker. **Required** in production. |
| `DISCORD_LINK_PATH` | string | `/settings/discord` | Frontend route used in Discord deep links. |
| `STRIPE_SECRET_KEY` | string | `sk_test_placeholder` | Stripe API key. **Replace for production**. |
| `STRIPE_PRICE_PRO` | string | `price_dev_pro` | Stripe price ID for Pro plan. |
| `STRIPE_PRICE_ELITE` | string | `price_dev_elite` | Stripe price ID for Elite plan. |
| `STRIPE_WEBHOOK_SECRET` | string | `whsec_dev` | Stripe webhook signing secret. |
| `STRIPE_WEBHOOK_FORWARD` | URL \| empty | _empty_ | Optional Stripe CLI forwarding URL. |
| `ANALYTICS_ENABLED` | bool | `false` | Enables event tracking and dashboards. |
| `ANALYTICS_SALT` | string | _empty_ | Required when analytics are enabled; salt for hashing user IDs. |
| `EMAIL_ENABLED` | bool | `false` | Enables transactional email sending. |
| `SMTP_URL` | URL | _empty_ | SMTP connection string used when `EMAIL_ENABLED=true`. Optional if SendGrid is used. |
| `SENDGRID_API_KEY` | string | _empty_ | Alternative provider when email is enabled. Domain must be verified in SendGrid (SPF/DKIM/DMARC) before enabling. |
| `EMAIL_FROM_ADDRESS` | string | `notifications@example.com` | Default 'From' address for transactional email. |
| `S3_ENABLED` | bool | `false` | Enables S3-compatible storage for assets/exports. |
| `S3_ENDPOINT` | URL | _empty_ | Required when S3 is enabled (supports AWS S3, MinIO, etc.). |
| `S3_REGION` | string | `us-east-1` | Region identifier used by the storage provider. |
| `S3_BUCKET` | string | `gridboss-dev` | Target bucket/container name. |
| `S3_ACCESS_KEY` | string | _empty_ | Access key for storage provider. |
| `S3_SECRET_KEY` | string | _empty_ | Secret key for storage provider. |
| `SENTRY_DSN` | URL \| empty | _empty_ | Optional Sentry DSN for error reporting. |
| `SENTRY_TRACES_SAMPLE_RATE` | float | `0.0` | Sampling rate for Sentry performance traces. |
| `VITE_SENTRY_DSN` | string | _empty_ | Frontend DSN used by the React bundle (when unset, Sentry is disabled). Prefixed with `VITE_` for Vite exposure. |
| `VITE_SENTRY_TRACES_SAMPLE_RATE` | float | `0` | Optional client-side traces sampling rate; ignored when DSN is empty. |
| `OTEL_ENABLED` | bool | `false` | Toggles OpenTelemetry exporters. |
| `OTEL_EXPORTER_ENDPOINT` | URL \| empty | _empty_ | Collector endpoint when OTEL is enabled. |
| `OTEL_SERVICE_NAME` | string | `gridboss-api` | Service name reported to OTEL/Sentry. |
| `HEALTH_CACHE_SECONDS` | int | `0` | Cache TTL for health endpoint responses. |

### Validation Rules

- The settings loader raises a validation error if any required key is blank or if production (`APP_ENV=production`) still uses the development sentinel values (`dev-jwt-secret`, `sk_test_placeholder`, etc.).
- When `ANALYTICS_ENABLED=true`, `ANALYTICS_SALT` must be supplied.
| `EMAIL_FROM_ADDRESS` | string | `notifications@example.com` | Default 'From' address for transactional email. |
- When `S3_ENABLED=true`, all of `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY` must be set.

Refer to `.env.example` for commented examples. Services can access configuration via `gridboss_config.get_settings()`, which returns the singleton `Settings` instance.
