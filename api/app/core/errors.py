from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def api_error(*, status_code: int, code: str, message: str, field: str | None = None) -> HTTPException:
    """Construct an HTTPException with our standard error envelope."""
    error_body: dict[str, Any] = {"code": code, "message": message}
    if field is not None:
        error_body["field"] = field
    return HTTPException(status_code=status_code, detail={"error": error_body})
