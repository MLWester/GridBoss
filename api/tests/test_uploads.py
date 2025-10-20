from __future__ import annotations

import boto3
from io import BytesIO

from fastapi.testclient import TestClient
from moto import mock_aws
from PIL import Image

from app.main import app
from app.services import storage
from gridboss_config import get_settings

client = TestClient(app)


def _reset_settings() -> None:
    get_settings.cache_clear()
    storage._cached_client.cache_clear()  # type: ignore[attr-defined]


@mock_aws
def test_sign_avatar_happy_path(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    monkeypatch.setenv("S3_PRESIGN_TTL", "600")

    _reset_settings()

    s3 = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test-access",
        aws_secret_access_key="test-secret",
    )
    s3.create_bucket(Bucket="gridboss-test")

    response = client.post(
        "/uploads/sign",
        json={
            "kind": "avatar",
            "filename": "driver-photo.png",
            "content_type": "image/png",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["bucket"] == "gridboss-test"
    assert data["contentType"] == "image/png"
    assert data["objectKey"].startswith("avatars/")
    assert data["maxSize"] == 2 * 1024 * 1024
    assert "Content-Type" in data["fields"]


@mock_aws
def test_sign_upload_unsupported_kind(monkeypatch) -> None:
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    _reset_settings()

    response = client.post(
        "/uploads/sign",
        json={
            "kind": "screenshot",
            "filename": "race.png",
            "content_type": "image/png",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"] == "unsupported_kind"


@mock_aws
def test_sign_upload_unsupported_content_type(monkeypatch) -> None:
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    _reset_settings()

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="gridboss-test")

    response = client.post(
        "/uploads/sign",
        json={
            "kind": "avatar",
            "filename": "driver.gif",
            "content_type": "image/gif",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"] == "unsupported_content_type"


@mock_aws
def test_complete_avatar_strips_exif(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    monkeypatch.setenv("S3_PRESIGN_TTL", "600")
    _reset_settings()

    s3 = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test-access",
        aws_secret_access_key="test-secret",
    )
    s3.create_bucket(Bucket="gridboss-test")

    image = Image.new("RGB", (10, 10), color=(128, 0, 128))
    exif = Image.Exif()
    exif[0x9003] = "2024:01:01 00:00:00"
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    raw_bytes = buffer.getvalue()

    object_key = "avatars/test-avatar.jpg"
    s3.put_object(
        Bucket="gridboss-test",
        Key=object_key,
        Body=raw_bytes,
        ContentType="image/jpeg",
    )

    response = client.post(
        "/uploads/complete",
        json={"kind": "avatar", "objectKey": object_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["objectKey"] == object_key
    assert "X-Amz-Signature" in data["url"]
    assert data["contentType"] == "image/jpeg"
    assert data["contentLength"] < len(raw_bytes)

    sanitized = s3.get_object(Bucket="gridboss-test", Key=object_key)["Body"].read()
    sanitized_image = Image.open(BytesIO(sanitized))
    assert not bool(sanitized_image.getexif())


@mock_aws
def test_sign_download_requires_matching_prefix(monkeypatch) -> None:
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    _reset_settings()

    response = client.post(
        "/uploads/download",
        json={"kind": "avatar", "objectKey": "exports/export.csv"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"] == "invalid_object_key"


@mock_aws
def test_complete_upload_missing_object(monkeypatch) -> None:
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    _reset_settings()

    response = client.post(
        "/uploads/complete",
        json={"kind": "avatar", "objectKey": "avatars/missing.jpg"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"] == "object_not_found"


@mock_aws
def test_sign_download_success(monkeypatch) -> None:
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    monkeypatch.setenv("S3_PRESIGN_TTL", "300")
    _reset_settings()

    s3 = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test-access",
        aws_secret_access_key="test-secret",
    )
    s3.create_bucket(Bucket="gridboss-test")
    object_key = "exports/report.csv"
    s3.put_object(
        Bucket="gridboss-test",
        Key=object_key,
        Body=b"driver_id,points\n1,25\n",
        ContentType="text/csv",
    )

    response = client.post(
        "/uploads/download",
        json={"kind": "export", "objectKey": object_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["expiresIn"] == 300
    assert "X-Amz-Signature" in data["url"]


@mock_aws
def test_complete_avatar_rejects_large_file(monkeypatch) -> None:
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET", "gridboss-test")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.amazonaws.com")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
    _reset_settings()

    s3 = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test-access",
        aws_secret_access_key="test-secret",
    )
    s3.create_bucket(Bucket="gridboss-test")

    object_key = "avatars/oversize.jpg"
    s3.put_object(
        Bucket="gridboss-test",
        Key=object_key,
        Body=b"x" * (2 * 1024 * 1024 + 1),
        ContentType="image/jpeg",
    )

    response = client.post(
        "/uploads/complete",
        json={"kind": "avatar", "objectKey": object_key},
    )

    assert response.status_code == 413
    body = response.json()
    assert body["detail"]["error"] == "object_too_large"
