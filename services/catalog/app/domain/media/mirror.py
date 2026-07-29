from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from app.domain.media.pack_io import (
    delete_mirrored_pack_archive_sync,
    mirror_pack_archive_sync,
    pack_archive_asset_id,
    zip_pack_directory,
)

__all__ = [
    "pack_archive_asset_id",
    "zip_pack_directory",
    "mirror_pack_archive",
    "delete_mirrored_pack_archive",
]


async def mirror_pack_archive(
    *,
    media_service_url: str,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    version: str,
    disk_path: Path,
) -> str | None:
                                                                             
    if not media_service_url:
        return None
    return await asyncio.to_thread(
        mirror_pack_archive_sync,
        media_service_url=media_service_url,
        user_id=user_id,
        pack_id=pack_id,
        version=version,
        disk_path=disk_path,
    )


async def delete_mirrored_pack_archive(
    *,
    media_service_url: str,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    version: str,
) -> None:
    if not media_service_url:
        return
    await asyncio.to_thread(
        delete_mirrored_pack_archive_sync,
        media_service_url=media_service_url,
        user_id=user_id,
        pack_id=pack_id,
        version=version,
    )
