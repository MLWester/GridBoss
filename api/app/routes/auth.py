from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import (
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.settings import Settings, get_settings
from app.db.models import BillingAccount, Membership, User
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.auth import BillingPlanOut, MembershipOut, MeResponse, TokenResponse, UserOut
from app.services.discord import DiscordOAuthClient, get_discord_client
from app.services.email import queue_transactional_email

router = APIRouter(prefix="/auth", tags=["auth"])

PKCE_COOKIE = "gb_pkce_verifier"
STATE_COOKIE = "gb_oauth_state"
REFRESH_COOKIE = "gb_refresh_token"
STATE_TTL_SECONDS = 300

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _set_refresh_cookie(response: Response, *, token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure(),
        samesite="lax",
        max_age=settings.jwt_refresh_ttl_days * 24 * 60 * 60,
    )


def _clear_oauth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(PKCE_COOKIE, secure=settings.cookie_secure(), samesite="lax")
    response.delete_cookie(STATE_COOKIE, secure=settings.cookie_secure(), samesite="lax")


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(REFRESH_COOKIE, secure=settings.cookie_secure(), samesite="lax")


def provide_discord_client(settings: SettingsDep) -> DiscordOAuthClient:
    return get_discord_client(settings)


DiscordClientDep = Annotated[DiscordOAuthClient, Depends(provide_discord_client)]


@router.get("/discord/start", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def discord_start(settings: SettingsDep) -> Response:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
        .rstrip(b"=")
        .decode()
    )
    state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": settings.discord_client_id,
        "scope": "identify email",
        "redirect_uri": str(settings.discord_redirect_uri),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"

    redirect = RedirectResponse(authorize_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    redirect.set_cookie(
        PKCE_COOKIE,
        value=verifier,
        max_age=STATE_TTL_SECONDS,
        secure=settings.cookie_secure(),
        httponly=True,
        samesite="lax",
    )
    redirect.set_cookie(
        STATE_COOKIE,
        value=state,
        max_age=STATE_TTL_SECONDS,
        secure=settings.cookie_secure(),
        httponly=True,
        samesite="lax",
    )
    return redirect


@router.get("/discord/callback", status_code=status.HTTP_302_FOUND)
async def discord_callback(
    request: Request,
    settings: SettingsDep,
    session: SessionDep,
    client: DiscordClientDep,
) -> Response:
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state")

    stored_state = request.cookies.get(STATE_COOKIE)
    verifier = request.cookies.get(PKCE_COOKIE)
    if stored_state is None or verifier is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth session expired")
    if stored_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state mismatch")

    try:
        token_payload = await client.exchange_code(code=code, code_verifier=verifier)
        user_payload = await client.fetch_user(access_token=token_payload["access_token"])
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Discord OAuth failed"
        ) from exc

    discord_id = user_payload.get("id")
    if not discord_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Discord user missing id"
        )

    user = session.execute(select(User).where(User.discord_id == discord_id)).scalar_one_or_none()
    is_new_user = user is None
    if user is None:
        user = User(discord_id=discord_id)
        session.add(user)

    user.discord_username = user_payload.get("username")
    user.avatar_url = user_payload.get("avatar")
    user.email = user_payload.get("email")
    user.is_active = True
    session.commit()

    if is_new_user and user.email:
        display_name = user.discord_username or "Racer"
        queue_transactional_email(
            template_id="welcome",
            recipient=user.email,
            context={
                "display_name": display_name,
                "app_url": str(settings.app_url),
            },
            actor_id=str(user.id),
        )

    access_token = create_access_token(subject=str(user.id), settings=settings)
    refresh_token = create_refresh_token(subject=str(user.id), settings=settings)

    redirect_url = f"{settings.app_url}?{urlencode({'access_token': access_token})}"
    redirect_response = RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)
    _set_refresh_cookie(redirect_response, token=refresh_token, settings=settings)
    _clear_oauth_cookies(redirect_response, settings=settings)
    redirect_response.headers["Cache-Control"] = "no-store"
    return redirect_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    settings: SettingsDep,
    session: SessionDep,
    refresh_cookie: RefreshCookie = None,
) -> TokenResponse:
    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    try:
        payload = decode_token(refresh_cookie, settings=settings, expected_type=REFRESH_TOKEN_TYPE)
    except TokenError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    try:
        user_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc

    user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = create_access_token(subject=str(user.id), settings=settings)
    new_refresh = create_refresh_token(subject=str(user.id), settings=settings)
    _set_refresh_cookie(response, token=new_refresh, settings=settings)
    return TokenResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: SettingsDep) -> Response:
    _clear_refresh_cookie(response, settings=settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
async def read_me(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> MeResponse:
    memberships_query = (
        select(Membership)
        .where(Membership.user_id == current_user.id)
        .options(joinedload(Membership.league))
    )
    memberships = session.execute(memberships_query).scalars().all()

    membership_out: list[MembershipOut] = [
        MembershipOut(
            league_id=item.league_id,
            league_slug=item.league.slug,
            league_name=item.league.name,
            role=item.role,
        )
        for item in memberships
    ]

    billing_account = session.execute(
        select(BillingAccount).where(BillingAccount.owner_user_id == current_user.id)
    ).scalar_one_or_none()

    billing = (
        BillingPlanOut(
            plan=billing_account.plan, current_period_end=billing_account.current_period_end
        )
        if billing_account
        else None
    )

    return MeResponse(
        user=UserOut.model_validate(current_user), memberships=membership_out, billingPlan=billing
    )
