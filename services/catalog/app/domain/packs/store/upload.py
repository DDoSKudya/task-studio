from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.pack import extract_pack_archive

from ..types import PackError, UploadedPack
from .upload_helpers import get_or_create_pack, persist_pack_version, reject_duplicate_version


async def upload_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    archive: bytes,
    *,
    packs_root: Path,
    max_upload_bytes: int,
    media_service_url: str = "",
) -> UploadedPack:
    if len(archive) > max_upload_bytes:
        raise PackError(413, "pack exceeds upload limit")

    pack_dir = packs_root / str(user_id)
    pack_dir.mkdir(parents=True, exist_ok=True)
    staging = pack_dir / f".upload-{uuid.uuid4()}"
    staging.mkdir(parents=True, exist_ok=True)

    try:
        parsed = await asyncio.to_thread(extract_pack_archive, archive, staging)
    except (ValueError, OSError) as exc:
        await asyncio.to_thread(shutil.rmtree, staging, True)
        raise PackError(422, str(exc)) from exc

    pack = await get_or_create_pack(session, user_id, parsed)
    await reject_duplicate_version(session, pack.id, parsed.version, staging)

    final_path = pack_dir / str(pack.id) / parsed.version

    final_path.parent.mkdir(parents=True, exist_ok=True)
    if final_path.exists():
        await asyncio.to_thread(shutil.rmtree, final_path)
    try:
        staging.rename(final_path)
    except OSError as exc:
        await asyncio.to_thread(shutil.rmtree, staging, True)
        raise PackError(500, "pack could not be stored on disk") from exc

    pack_version = await persist_pack_version(
        session,
        user_id,
        pack,
        parsed,
        final_path,
        media_service_url=media_service_url,
    )
    return UploadedPack(
        pack_id=pack.id,
        version_id=pack_version.id,
        slug=parsed.slug,
        title=parsed.title,
        version=parsed.version,
    )
