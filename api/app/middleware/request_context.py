from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.observability import (
    bind_league_id,
    bind_request_id,
    bind_user_id,
    clear_context,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request-scoped context for observability."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        incoming_request_id = request.headers.get("X-Request-ID") or str(uuid4())
        bind_request_id(incoming_request_id)
        bind_user_id(None)
        bind_league_id(None)
        request.state.request_id = incoming_request_id

        try:
            response = await call_next(request)
        finally:
            clear_context()

        if "X-Request-ID" not in response.headers:
            response.headers["X-Request-ID"] = incoming_request_id
        return response
