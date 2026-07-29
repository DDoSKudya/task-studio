from __future__ import annotations

import uuid
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.config import MediaSettings
from app.storage_stream import get_object_stream, remove_object

__all__ = [
    "build_client",
    "ensure_bucket",
    "user_object_key",
    "put_object_bytes",
    "object_exists",
    "get_object_stream",
    "remove_object",
]


def build_client(settings: MediaSettings) -> Minio:
    return Minio(
        settings.endpoint,
        access_key=settings.access_key,
        secret_key=settings.secret_key,
        secure=settings.secure,
    )


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def user_object_key(user_id: uuid.UUID, asset_id: str) -> str:
    return f"users/{user_id}/{asset_id.lstrip('/')}"


def put_object_bytes(
    client: Minio,
    settings: MediaSettings,
    object_key: str,
    data: bytes,
    *,
    content_type: str,
) -> None:
    client.put_object(
        settings.bucket,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )


def object_exists(client: Minio, settings: MediaSettings, object_key: str) -> bool:
    try:
        client.stat_object(settings.bucket, object_key)
    except S3Error as exc:
        if getattr(exc, "code", None) == "NoSuchKey":
            return False
        raise
    return True
