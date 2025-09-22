from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from fastapi import HTTPException, status

from app.core.settings import Settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105
REFRESH_TOKEN_TYPE = "refresh"  # noqa: S105


class TokenError(HTTPException):
    def __init__(
        self, detail: str = "Invalid token", status_code: int = status.HTTP_401_UNAUTHORIZED
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)


def _create_token(
    *, data: dict[str, Any], expires_delta: timedelta, settings: Settings, token_type: str
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta  # noqa: UP017
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(*, subject: str, settings: Settings) -> str:
    expires = timedelta(minutes=settings.jwt_access_ttl_min)
    return _create_token(
        data={"sub": subject},
        expires_delta=expires,
        settings=settings,
        token_type=ACCESS_TOKEN_TYPE,
    )


def create_refresh_token(*, subject: str, settings: Settings) -> str:
    expires = timedelta(days=settings.jwt_refresh_ttl_days)
    token_id = secrets.token_urlsafe(32)
    return _create_token(
        data={"sub": subject, "jti": token_id},
        expires_delta=expires,
        settings=settings,
        token_type=REFRESH_TOKEN_TYPE,
    )


def decode_token(
    token: str, *, settings: Settings, expected_type: Literal["access", "refresh"]
) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError(detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError() from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise TokenError(detail="Incorrect token type")

    subject = payload.get("sub")
    if subject is None:
        raise TokenError(detail="Token missing subject")

    return payload
