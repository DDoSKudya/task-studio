from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.infra.models import Pack, PackVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.pack import ParsedManifest

from ..types import PackError
from .upload_persist import persist_pack_version

__all__ = [
    "get_or_create_pack",
    "reject_duplicate_version",
    "persist_pack_version",
]


async def get_or_create_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedManifest,
) -> Pack:
    result = await session.execute(
        select(Pack).where(Pack.owner_user_id == user_id, Pack.slug == parsed.slug),
    )
    pack = result.scalar_one_or_none()
    if pack is None:
        pack = Pack(
            owner_user_id=user_id,
            slug=parsed.slug,
            title=parsed.title,
            source=parsed.source,
            schema_version=parsed.schema_version,
        )
        session.add(pack)
        await session.flush()
        return pack

    pack.title = parsed.title
    pack.schema_version = parsed.schema_version
    return pack


async def reject_duplicate_version(
    session: AsyncSession,
    pack_id: uuid.UUID,
    version: str,
    staging: Path,
    *,
    cleanup_on_conflict: bool = True,
) -> None:
    existing = await session.execute(
        select(PackVersion).where(PackVersion.pack_id == pack_id, PackVersion.version == version),
    )
    if existing.scalar_one_or_none() is not None:
        if cleanup_on_conflict:
            shutil.rmtree(staging, ignore_errors=True)
        raise PackError(409, "pack version already exists")
