from __future__ import annotations

import uuid
from pathlib import Path

from app.infra.models import PackVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.pack import parse_manifest

from ..types import UploadedPack
from .register_create import create_imported_pack_version
from .register_helpers import get_or_create_imported_pack
from .register_update import update_existing_imported_version


async def register_imported_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    manifest: dict[str, object],
    disk_path: Path,
    external_id: str,
    source: str,
    import_report: dict[str, object] | None,
    object_key: str | None = None,
    media_service_url: str = "",
) -> UploadedPack:
    parsed = parse_manifest(manifest)

    pack = await get_or_create_imported_pack(
        session,
        user_id,
        parsed,
        external_id=external_id,
        source=source,
    )

    existing = await session.execute(
        select(PackVersion).where(
            PackVersion.pack_id == pack.id,
            PackVersion.version == parsed.version,
        ),
    )
    pack_version = existing.scalar_one_or_none()
    if pack_version is not None:
        return await update_existing_imported_version(
            session,
            user_id=user_id,
            pack_id=pack.id,
            pack_version=pack_version,
            parsed=parsed,
            disk_path=disk_path,
            import_report=import_report,
            object_key=object_key,
            media_service_url=media_service_url,
        )

    return await create_imported_pack_version(
        session,
        user_id,
        pack=pack,
        parsed=parsed,
        disk_path=disk_path,
        import_report=import_report,
        object_key=object_key,
        media_service_url=media_service_url,
    )
