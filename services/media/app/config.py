from __future__ import annotations

import os
from dataclasses import dataclass

_PRESIGN_TTL_MAX = 900
_PRESIGN_TTL_MIN = 60


@dataclass(frozen=True, slots=True)
class MediaSettings:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    secure: bool
    presign_ttl_seconds: int


def clamp_presign_ttl_seconds(raw: int) -> int:
    return max(_PRESIGN_TTL_MIN, min(raw, _PRESIGN_TTL_MAX))


def load_settings() -> MediaSettings:
    return MediaSettings(
        endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "studio"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "studio-secret"),
        bucket=os.getenv("MINIO_BUCKET", "studio"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        presign_ttl_seconds=clamp_presign_ttl_seconds(
            int(os.getenv("MINIO_PRESIGN_TTL_SECONDS", "900"))
        ),
    )
