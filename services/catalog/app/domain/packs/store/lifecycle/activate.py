from __future__ import annotations

import uuid

from app.infra.models import PackVersion, UserPack
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...types import PackError


async def activate_pack_version(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    version: str,
) -> PackVersion:
    installation = await session.get(UserPack, (user_id, pack_id))
    if installation is None:
        raise PackError(404, "pack not found")

    result = await session.execute(
        select(PackVersion).where(PackVersion.pack_id == pack_id, PackVersion.version == version),
    )
    pack_version = result.scalar_one_or_none()
    if pack_version is None:
        raise PackError(404, "pack version not found")

    installation.pack_version_id = pack_version.id
    installation.active = True
    await session.commit()
    await session.refresh(pack_version)
    return pack_version
