from __future__ import annotations

import json
import sys
import types

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
    stripe_module.Customer = types.SimpleNamespace(create=lambda **kwargs: {"id": "stub_customer"})
    stripe_module.checkout = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_checkout"}))
    stripe_module.billing_portal = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_portal"}))
    stripe_module.Webhook = types.SimpleNamespace(construct_event=staticmethod(_construct_event))
    stripe_module.error = types.SimpleNamespace(SignatureVerificationError=_StripeSignatureError)
    sys.modules["stripe"] = stripe_module
