from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from typing import Literal
from uuid import uuid4

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from PIL import Image, ImageFile

from app.core.settings import Settings, get_settings


AllowedUploadKind = Literal["avatar", "export"]


@dataclass(frozen=True)
class UploadProfile:
    prefix: str
    max_size: int
    content_types: dict[str, str]
    strip_exif: bool = False


PROFILES: dict[AllowedUploadKind, UploadProfile] = {
    "avatar": UploadProfile(
        prefix="avatars/",
        max_size=2 * 1024 * 1024,
        content_types={
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        },
        strip_exif=True,
    ),
    "export": UploadProfile(
        prefix="exports/",
        max_size=25 * 1024 * 1024,
        content_types={
            "text/csv": ".csv",
            "application/json": ".json",
            "application/pdf": ".pdf",
            "application/zip": ".zip",
        },
    ),
}

_FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]")
_IMAGE_FORMAT_BY_CONTENT_TYPE = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}

ImageFile.LOAD_TRUNCATED_IMAGES = True


def _sanitize_extension(filename: str) -> str:
    # fall back to empty extension so configured mapping can decide
    dot_index = filename.rfind(".")
    if dot_index != -1:
        return filename[dot_index:].lower()
    return ""


@lru_cache(maxsize=4)
def _cached_client(endpoint: str, access_key: str, secret_key: str, region: str | None):
    session = boto3.session.Session()
    return session.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region or None,
        endpoint_url=endpoint or None,
        config=BotoConfig(signature_version="s3v4"),
    )


def _get_s3_client(settings: Settings):
    if not settings.s3_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "s3_not_enabled", "message": "S3 uploads are not enabled."},
        )

    return _cached_client(
        str(settings.s3_endpoint) if settings.s3_endpoint else "",
        settings.s3_access_key or "",
        settings.s3_secret_key or "",
        settings.s3_region,
    )


def _build_object_key(profile: UploadProfile, filename: str, content_type: str) -> str:
    stripped = _FILENAME_SANITIZER.sub("-", filename).strip("-")
    ext_from_name = _sanitize_extension(stripped)
    ext = profile.content_types.get(content_type)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "unsupported_content_type", "message": f"Content type {content_type} is not allowed."},
        )

    if not ext and ext_from_name:
        ext = ext_from_name

    return f"{profile.prefix}{uuid4().hex}{ext}"


def generate_presigned_post(kind: AllowedUploadKind, filename: str, content_type: str, settings: Settings | None = None) -> dict:
    active_settings = settings or get_settings()
    profile = PROFILES[kind]
    object_key = _build_object_key(profile, filename, content_type)
    client = _get_s3_client(active_settings)

    try:
        presigned = client.generate_presigned_post(
            Bucket=active_settings.s3_bucket,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, profile.max_size],
            ],
            ExpiresIn=active_settings.s3_presign_ttl or 3600,
        )
    except Exception as exc:  # pragma: no cover - boto errors vary
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "s3_presign_failed", "message": str(exc)},
        ) from exc

    return {
        "url": presigned["url"],
        "fields": presigned["fields"],
        "objectKey": object_key,
        "bucket": active_settings.s3_bucket,
        "maxSize": profile.max_size,
        "contentType": content_type,
        "expiresIn": active_settings.s3_presign_ttl or 3600,
    }


def generate_presigned_get_url(object_key: str, settings: Settings | None = None, expires_in: int | None = None) -> dict:
    active_settings = settings or get_settings()
    client = _get_s3_client(active_settings)
    ttl = expires_in or active_settings.s3_presign_ttl or 3600

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": active_settings.s3_bucket, "Key": object_key},
            ExpiresIn=ttl,
        )
    except Exception as exc:  # pragma: no cover - boto errors vary
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "s3_presign_failed", "message": str(exc)},
        ) from exc

    return {"url": url, "expiresIn": ttl}


def finalize_upload(kind: AllowedUploadKind, object_key: str, settings: Settings | None = None) -> dict:
    active_settings = settings or get_settings()
    profile = PROFILES[kind]

    if not object_key.startswith(profile.prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_object_key", "message": "Object key does not match the expected prefix."},
        )

    client = _get_s3_client(active_settings)

    try:
        head = client.head_object(Bucket=active_settings.s3_bucket, Key=object_key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NoSuchBucket", "NotFound"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "object_not_found", "message": "Uploaded object could not be located."},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "s3_head_failed", "message": str(exc)},
        ) from exc

    content_length = head.get("ContentLength", 0)
    content_type = head.get("ContentType")

    if content_length == 0 or content_length > profile.max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "object_too_large", "message": "Uploaded object exceeds configured size limits."},
        )

    if not content_type or content_type not in profile.content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "unsupported_content_type", "message": f"Content type {content_type!r} is not allowed."},
        )

    if profile.strip_exif:
        content_length = _strip_exif_in_place(
            client=client,
            bucket=active_settings.s3_bucket,
            object_key=object_key,
            content_type=content_type,
            max_size=profile.max_size,
        )

    presigned = generate_presigned_get_url(object_key, settings=active_settings)

    return {
        "objectKey": object_key,
        "contentType": content_type,
        "contentLength": content_length,
        "url": presigned["url"],
        "expiresIn": presigned["expiresIn"],
    }


def _strip_exif_in_place(
    client,
    bucket: str,
    object_key: str,
    content_type: str,
    max_size: int,
) -> int:
    try:
        obj = client.get_object(Bucket=bucket, Key=object_key)
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "s3_fetch_failed", "message": str(exc)},
        ) from exc

    body = obj["Body"]
    try:
        data = body.read()
    finally:
        body.close()

    if len(data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "object_too_large", "message": "Uploaded object exceeds configured size limits."},
        )

    try:
        image = Image.open(BytesIO(data))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_image", "message": f"Unable to process uploaded image: {exc}"},
        ) from exc

    image_format = _IMAGE_FORMAT_BY_CONTENT_TYPE.get(content_type) or image.format
    if not image_format:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "unsupported_content_type", "message": f"Content type {content_type!r} is not allowed."},
        )

    if image_format == "JPEG":
        image = image.convert("RGB")

    output = BytesIO()
    save_kwargs: dict[str, object] = {"format": image_format}
    if image_format == "JPEG":
        save_kwargs.update({"optimize": True, "quality": 92, "progressive": True})
    elif image_format == "PNG":
        save_kwargs.update({"optimize": True})
    elif image_format == "WEBP":
        save_kwargs.update({"quality": 92})

    image.save(output, **save_kwargs)
    sanitized_bytes = output.getvalue()

    try:
        client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=sanitized_bytes,
            ContentType=content_type,
        )
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "s3_write_failed", "message": str(exc)},
        ) from exc

    return len(sanitized_bytes)
