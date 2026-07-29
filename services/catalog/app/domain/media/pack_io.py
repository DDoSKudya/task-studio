from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import structlog
from app.domain.media.pack_delete import delete_mirrored_pack_archive_sync
from app.domain.media.pack_encode import (
    multipart_body,
    pack_archive_asset_id,
    zip_pack_directory,
)

log = structlog.get_logger("catalog.media_mirror")

__all__ = [
    "pack_archive_asset_id",
    "zip_pack_directory",
    "multipart_body",
    "mirror_pack_archive_sync",
    "delete_mirrored_pack_archive_sync",
]


def mirror_pack_archive_sync(
    *,
    media_service_url: str,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    version: str,
    disk_path: Path,
) -> str | None:
    root = Path(disk_path)
    if not root.is_dir():
        return None
    try:
        payload = zip_pack_directory(root)
    except OSError as exc:
        log.warning("pack_zip_failed", pack_id=str(pack_id), error=str(exc))
        return None
    if not payload:
        return None

    asset_id = pack_archive_asset_id(pack_id, version)
    body, content_type = multipart_body(asset_id, payload)
    request = Request(
        f"{media_service_url}/internal/v1/media/upload",
        data=body,
        method="POST",
        headers={
            "X-User-Id": str(user_id),
            "Content-Type": content_type,
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
        object_key = json.loads(raw).get("object_key")
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError) as exc:
        log.warning("pack_mirror_failed", pack_id=str(pack_id), error=str(exc))
        return None
    return object_key if isinstance(object_key, str) and object_key else None
