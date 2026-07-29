from __future__ import annotations

import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import structlog
from app.domain.media.pack_encode import pack_archive_asset_id

log = structlog.get_logger("catalog.media_mirror")


def delete_mirrored_pack_archive_sync(
    *,
    media_service_url: str,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    version: str,
) -> None:
    asset_id = pack_archive_asset_id(pack_id, version)
    request = Request(
        f"{media_service_url}/internal/v1/media/{asset_id}",
        method="DELETE",
        headers={"X-User-Id": str(user_id)},
    )
    try:
        with urlopen(request, timeout=15) as response:
            response.read()
    except HTTPError as exc:
        if exc.code != 404:
            log.warning("pack_mirror_delete_failed", pack_id=str(pack_id), error=str(exc))
    except (URLError, TimeoutError) as exc:
        log.warning("pack_mirror_delete_failed", pack_id=str(pack_id), error=str(exc))
