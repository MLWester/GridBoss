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
