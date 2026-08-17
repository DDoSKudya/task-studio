from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.domain.media.mirror import mirror_pack_archive
from app.domain.packs.store.lifecycle.install import upsert_installation
from app.infra.models import Pack, PackVersion
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.packs.pack import ParsedManifest

from ...types import PackError


async def persist_pack_version(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack: Pack,
    parsed: ParsedManifest,
    final_path: Path,
    *,
    media_service_url: str = "",
    object_key: str | None = None,
) -> PackVersion:
    pack_version = PackVersion(
        pack_id=pack.id,
        version=parsed.version,
        manifest=parsed.raw,
        disk_path=str(final_path),
        object_key=object_key,
    )
    session.add(pack_version)
    await session.flush()
    await upsert_installation(session, user_id, pack.id, pack_version.id)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        shutil.rmtree(final_path, ignore_errors=True)
        raise PackError(422, "pack could not be saved") from exc

    if not pack_version.object_key:
        mirrored = await mirror_pack_archive(
            media_service_url=media_service_url,
            user_id=user_id,
            pack_id=pack.id,
            version=parsed.version,
            disk_path=final_path,
        )
        if mirrored:
            pack_version.object_key = mirrored
            await session.commit()

    return pack_version
