from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path

import structlog
from app.domain.media.mirror import delete_mirrored_pack_archive
from app.infra.models import Pack, PackVersion, UserPack
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...types import PackError

log = structlog.get_logger("catalog.packs_delete")


async def _delete_mirrored_archives(
    mirrored: list[tuple[str, str]],
    *,
    media_service_url: str,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> None:
    limit = asyncio.Semaphore(4)

    async def delete_one(version: str) -> None:
        async with limit:
            try:
                await delete_mirrored_pack_archive(
                    media_service_url=media_service_url,
                    user_id=user_id,
                    pack_id=pack_id,
                    version=version,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "mirrored_pack_archive_delete_failed",
                    pack_id=str(pack_id),
                    version=version,
                    error=str(exc),
                )

    await asyncio.gather(*(delete_one(version) for version, _object_key in mirrored))


async def _delete_pack_files(
    disk_paths: list[str],
    *,
    packs_root: Path,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> None:
    user_root = packs_root / str(user_id)
    for disk_path in disk_paths:
        try:
            path = Path(disk_path)
            await asyncio.to_thread(shutil.rmtree, path, True)
            parent = path.parent
            if parent != user_root and parent.is_relative_to(user_root):
                try:
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                except OSError:
                    pass
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "pack_disk_delete_failed",
                pack_id=str(pack_id),
                disk_path=disk_path,
                error=str(exc),
            )


async def _delete_pack_workdirs(
    *,
    packs_root: Path,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> None:
    try:
        await asyncio.to_thread(shutil.rmtree, packs_root / str(user_id) / str(pack_id), True)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "pack_user_root_delete_failed",
            pack_id=str(pack_id),
            error=str(exc),
        )

    staging = packs_root / "staging" / str(user_id)
    try:
        if staging.is_dir():
            for item in staging.iterdir():
                if item.is_file() and pack_id.hex[:8] in item.name:
                    item.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "pack_staging_cleanup_failed",
            pack_id=str(pack_id),
            error=str(exc),
        )


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
    disk_paths: list[str] = []
    mirrored: list[tuple[str, str]] = []
    for pack_version in versions:
        disk_path = pack_version.disk_path
        if isinstance(disk_path, str) and disk_path.strip():
            disk_paths.append(disk_path)

        obj_key = pack_version.object_key
        if isinstance(obj_key, str) and obj_key.strip():
            mirrored.append((pack_version.version, obj_key))

    await session.delete(installation)
    for pack_version in versions:
        await session.delete(pack_version)
    await session.delete(pack)
    await session.commit()

    if mirrored:
        await _delete_mirrored_archives(
            mirrored,
            media_service_url=media_service_url,
            user_id=user_id,
            pack_id=pack_id,
        )
    await _delete_pack_files(
        disk_paths,
        packs_root=packs_root,
        user_id=user_id,
        pack_id=pack_id,
    )
    await _delete_pack_workdirs(packs_root=packs_root, user_id=user_id, pack_id=pack_id)
