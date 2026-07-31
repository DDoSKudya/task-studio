from __future__ import annotations

import uuid
from pathlib import Path

from app.domain.media.mirror import mirror_pack_archive
from app.domain.packs.store.register_lookup import get_or_create_imported_pack
from app.infra.models import PackVersion
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "ensure_object_key",
    "get_or_create_imported_pack",
]


async def ensure_object_key(
    session: AsyncSession,
    pack_version: PackVersion,
    *,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    version: str,
    disk_path: Path,
    media_service_url: str,
) -> None:
    if pack_version.object_key:
        return
    mirrored = await mirror_pack_archive(
        media_service_url=media_service_url,
        user_id=user_id,
        pack_id=pack_id,
        version=version,
        disk_path=disk_path,
    )
    if not mirrored:
        return
    pack_version.object_key = mirrored
    await session.commit()
