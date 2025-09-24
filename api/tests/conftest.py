from __future__ import annotations

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
    stripe_module = types.ModuleType("stripe")
    stripe_module.Customer = types.SimpleNamespace(create=lambda **kwargs: {"id": "stub_customer"})
    stripe_module.checkout = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_checkout"}))
    stripe_module.billing_portal = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **kwargs: {"url": "stub_portal"}))
    stripe_module.error = types.SimpleNamespace(StripeError=Exception)
    sys.modules["stripe"] = stripe_module
