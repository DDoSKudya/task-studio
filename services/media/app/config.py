from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import timedelta

from minio import Minio
from minio.error import S3Error


@dataclass(frozen=True, slots=True)
class MediaSettings:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    secure: bool
    presign_ttl_seconds: int


def load_settings() -> MediaSettings:
    return MediaSettings(
        endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "studio"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "studio-secret"),
        bucket=os.getenv("MINIO_BUCKET", "studio"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        presign_ttl_seconds=int(os.getenv("MINIO_PRESIGN_TTL_SECONDS", "3600")),
    )


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


def presign_get_url(client: Minio, settings: MediaSettings, object_key: str) -> str:
    return client.presigned_get_object(
        settings.bucket,
        object_key,
        expires=timedelta(seconds=settings.presign_ttl_seconds),
    )


def object_exists(client: Minio, settings: MediaSettings, object_key: str) -> bool:
    try:
        client.stat_object(settings.bucket, object_key)
    except S3Error as exc:
        if exc.code == "NoSuchKey":
            return False
        raise
    return True
