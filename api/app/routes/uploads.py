from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.settings import Settings, get_settings
from app.services.storage import (
    AllowedUploadKind,
    PROFILES,
    finalize_upload,
    generate_presigned_get_url,
    generate_presigned_post,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


class SignedUploadRequest(BaseModel):
    kind: str = Field(description="Type of upload being performed.")
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)


class SignedUploadResponse(BaseModel):
    url: str
    fields: dict[str, str]
    objectKey: str
    bucket: str
    maxSize: int
    contentType: str
    expiresIn: int


class SignedGetRequest(BaseModel):
    kind: str = Field(description="Type of asset to access.")
    objectKey: str = Field(min_length=1, max_length=255)


class SignedGetResponse(BaseModel):
    url: str
    expiresIn: int


class CompleteUploadRequest(BaseModel):
    kind: str = Field(description="Type of upload being performed.")
    objectKey: str = Field(min_length=1, max_length=512)


class CompleteUploadResponse(BaseModel):
    objectKey: str
    url: str
    expiresIn: int
    contentType: str
    contentLength: int


@router.post("/sign", response_model=SignedUploadResponse)
async def sign_upload(
    payload: SignedUploadRequest,
    settings: Settings = Depends(get_settings),
) -> SignedUploadResponse:
    if payload.kind not in PROFILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "unsupported_kind", "message": f"Upload kind '{payload.kind}' is not supported."},
        )

    presigned = generate_presigned_post(
        kind=cast(AllowedUploadKind, payload.kind),
        filename=payload.filename,
        content_type=payload.content_type,
        settings=settings,
    )
    return SignedUploadResponse(**presigned)


@router.post("/download", response_model=SignedGetResponse)
async def sign_download(
    payload: SignedGetRequest,
    settings: Settings = Depends(get_settings),
) -> SignedGetResponse:
    profile = PROFILES.get(payload.kind)
    if not profile or not payload.objectKey.startswith(profile.prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_object_key", "message": "Object key does not match the expected prefix."},
        )

    presigned = generate_presigned_get_url(
        object_key=payload.objectKey,
        settings=settings,
    )
    return SignedGetResponse(**presigned)


@router.post("/complete", response_model=CompleteUploadResponse)
async def complete_upload(
    payload: CompleteUploadRequest,
    settings: Settings = Depends(get_settings),
) -> CompleteUploadResponse:
    finalized = finalize_upload(
        kind=cast(AllowedUploadKind, payload.kind),
        object_key=payload.objectKey,
        settings=settings,
    )
    return CompleteUploadResponse(**finalized)
