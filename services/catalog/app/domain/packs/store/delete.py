from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.domain.media.mirror import delete_mirrored_pack_archive
from app.infra.models import Pack, PackVersion, UserPack
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..types import PackError


async def delete_user_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    *,
    packs_root: Path,
    media_service_url: str = "",
) -> None:
    pack = await session.get(Pack, pack_id)
    if pack is None or pack.owner_user_id != user_id:
        raise PackError(404, "pack not found")

    installation = await session.get(UserPack, (user_id, pack_id))
    if installation is None:
        raise PackError(404, "pack not found")

    versions_result = await session.execute(
        select(PackVersion).where(PackVersion.pack_id == pack_id),
    )
    versions = list(versions_result.scalars())
    disk_paths = [pack_version.disk_path for pack_version in versions]
    mirrored = [
        (pack_version.version, pack_version.object_key)
        for pack_version in versions
        if pack_version.object_key
    ]

    await session.delete(installation)
    await session.delete(pack)
    await session.commit()

    for version, _object_key in mirrored:
        await delete_mirrored_pack_archive(
            media_service_url=media_service_url,
            user_id=user_id,
            pack_id=pack_id,
            version=version,
        )

    for disk_path in disk_paths:
        path = Path(disk_path)
        shutil.rmtree(path, ignore_errors=True)
                                                                                        
        parent = path.parent
        user_root = packs_root / str(user_id)
        if parent != user_root and parent.is_relative_to(user_root):
            try:
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass
    shutil.rmtree(packs_root / str(user_id) / str(pack_id), ignore_errors=True)
    staging = packs_root / "staging" / str(user_id)
    if staging.is_dir():
        for item in staging.iterdir():
            if item.is_file() and pack_id.hex[:8] in item.name:
                item.unlink(missing_ok=True)
