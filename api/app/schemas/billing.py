from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel


class CheckoutRequest(BaseModel):
    plan: Literal["PRO", "ELITE"]


class CheckoutResponse(BaseModel):
    url: AnyHttpUrl


class PortalResponse(BaseModel):
    url: AnyHttpUrl
