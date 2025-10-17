from __future__ import annotations

import json
import os
import sys
import types

TEST_ENV_DEFAULTS = {
    "APP_ENV": "test",
    "APP_URL": "http://localhost:5173",
    "API_URL": "http://localhost:8000",
    "API_PORT": "8000",
    "ADMIN_MODE": "false",
    "CORS_ORIGINS": "http://localhost:5173",
    "JWT_SECRET": "test-jwt-secret",
    "JWT_ACCESS_TTL_MIN": "15",
    "JWT_REFRESH_TTL_DAYS": "14",
    "DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/gridboss",
    "REDIS_URL": "redis://localhost:6379/0",
    "WORKER_THREADS": "8",
    "WORKER_NAME": "gridboss-worker",
    "WORKER_RETRY_MIN_BACKOFF_MS": "1000",
    "WORKER_RETRY_MAX_BACKOFF_MS": "300000",
    "WORKER_RETRY_MAX_RETRIES": "5",
    "DISCORD_CLIENT_ID": "123456789012345678",
    "DISCORD_CLIENT_SECRET": "test-discord-secret",
    "DISCORD_REDIRECT_URI": "http://localhost:8000/auth/discord/callback",
    "DISCORD_BOT_TOKEN": "test-bot-token",
    "DISCORD_LINK_PATH": "/settings/discord",
    "STRIPE_SECRET_KEY": "sk_test_placeholder",
    "STRIPE_PRICE_PRO": "price_test_pro",
    "STRIPE_PRICE_ELITE": "price_test_elite",
    "STRIPE_WEBHOOK_SECRET": "whsec_test",
    "ANALYTICS_ENABLED": "false",
    "EMAIL_ENABLED": "false",
    "S3_ENABLED": "false",
}

for _key, _value in TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)


if "dramatiq" not in sys.modules:

    class _ActorStub:
        def __init__(self, fn):
            self.fn = fn

        def send(self, *args, **kwargs):  # pragma: no cover - stub implementation
            return None

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    def _actor(*_args, **_kwargs):
        def decorator(fn):
            return _ActorStub(fn)

        return decorator

    module = types.ModuleType("dramatiq")
    module.actor = _actor
    sys.modules["dramatiq"] = module


if "stripe" not in sys.modules:

    class _StripeSignatureError(Exception):
        pass

    def _construct_event(payload: str, signature: str, secret: str):
        if signature != secret:
            raise _StripeSignatureError("invalid signature")
        return json.loads(payload)

    stripe_module = types.ModuleType("stripe")
    stripe_module.Customer = types.SimpleNamespace(
        create=lambda **kwargs: {"id": "stub_customer"}
    )
    stripe_module.checkout = types.SimpleNamespace(
        Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_checkout"})
    )
    stripe_module.billing_portal = types.SimpleNamespace(
        Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_portal"})
    )
    stripe_module.Webhook = types.SimpleNamespace(
        construct_event=staticmethod(_construct_event)
    )
    stripe_module.error = types.SimpleNamespace(
        SignatureVerificationError=_StripeSignatureError
    )
    sys.modules["stripe"] = stripe_module
