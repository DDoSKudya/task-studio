from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.domain.packs.store.lifecycle.install import upsert_installation
from app.domain.packs.store.registry.register_helpers import ensure_object_key
from app.infra.models import PackVersion
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.packs.pack import ParsedManifest

from ...types import PackError, UploadedPack


async def update_existing_imported_version(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    pack_version: PackVersion,
    parsed: ParsedManifest,
    disk_path: Path,
    import_report: dict[str, object] | None,
    object_key: str | None,
    media_service_url: str,
) -> UploadedPack:
    old_path = Path(pack_version.disk_path) if pack_version.disk_path else None
    pack_version.manifest = parsed.raw
    pack_version.disk_path = str(disk_path)
    pack_version.import_report = import_report
    if object_key:
        pack_version.object_key = object_key
    await session.flush()
    await upsert_installation(session, user_id, pack_id, pack_version.id)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PackError(409, "pack version already exists") from exc
    if old_path is not None and old_path != disk_path:
        shutil.rmtree(old_path, ignore_errors=True)
    await ensure_object_key(
        session,
        pack_version,
        user_id=user_id,
        pack_id=pack_id,
        version=parsed.version,
        disk_path=disk_path,
        media_service_url=media_service_url,
    )
    return UploadedPack(
        pack_id=pack_id,
        version_id=pack_version.id,
        slug=parsed.slug,
        title=parsed.title,
        version=parsed.version,
    )
