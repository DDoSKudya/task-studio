from __future__ import annotations

from collections.abc import Iterator

from minio import Minio
from minio.error import S3Error

from app.config import MediaSettings


def get_object_stream(
    client: Minio,
    settings: MediaSettings,
    object_key: str,
) -> tuple[Iterator[bytes], str | None, int | None]:
    response = client.get_object(settings.bucket, object_key)
    content_type = None
    length = None
    try:
        content_type = response.headers.get("Content-Type")
        raw_len = response.headers.get("Content-Length")
        if raw_len and raw_len.isdigit():
            length = int(raw_len)
    except (TypeError, ValueError, AttributeError):
        pass

    def _iter() -> Iterator[bytes]:
        try:
            yield from response.stream(32 * 1024)
        finally:
            response.close()
            response.release_conn()

    return _iter(), content_type, length


def remove_object(client: Minio, settings: MediaSettings, object_key: str) -> None:
    try:
        client.remove_object(settings.bucket, object_key)
    except S3Error as exc:
        if getattr(exc, "code", None) == "NoSuchKey":
            return
        raise
