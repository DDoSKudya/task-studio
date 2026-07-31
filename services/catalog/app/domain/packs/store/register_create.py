from __future__ import annotations

import uuid
from pathlib import Path

from app.infra.models import Pack, PackVersion
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.pack import ParsedManifest

from ..types import PackError, UploadedPack
from .install import upsert_installation
from .register_helpers import ensure_object_key


async def create_imported_pack_version(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    pack: Pack,
    parsed: ParsedManifest,
    disk_path: Path,
    import_report: dict[str, object] | None,
    object_key: str | None,
    media_service_url: str,
) -> UploadedPack:
    pack_version = PackVersion(
        pack_id=pack.id,
        version=parsed.version,
        manifest=parsed.raw,
        disk_path=str(disk_path),
        import_report=import_report,
        object_key=object_key,
    )
    session.add(pack_version)
    await session.flush()
    await upsert_installation(session, user_id, pack.id, pack_version.id)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PackError(409, "pack version already exists") from exc

    await ensure_object_key(
        session,
        pack_version,
        user_id=user_id,
        pack_id=pack.id,
        version=parsed.version,
        disk_path=disk_path,
        media_service_url=media_service_url,
    )

    return UploadedPack(
        pack_id=pack.id,
        version_id=pack_version.id,
        slug=parsed.slug,
        title=parsed.title,
        version=parsed.version,
    )
