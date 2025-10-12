from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.observability import bind_user_id
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.core.settings import Settings, get_settings
from app.db.models import User
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]
CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    request: Request,
    session: SessionDep,
    credentials: CredentialsDep,
    settings: SettingsDep,
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")

    payload = decode_token(
        credentials.credentials, settings=settings, expected_type=ACCESS_TOKEN_TYPE
    )
    subject = payload.get("sub")
    try:
        user_id = UUID(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc

    user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    request.state.user_id = str(user.id)
    bind_user_id(str(user.id))
    return user
