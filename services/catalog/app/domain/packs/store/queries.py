from __future__ import annotations

import uuid
from datetime import datetime

from app.domain.packs.store.lifecycle.activate import activate_pack_version
from app.domain.packs.store.lifecycle.delete import delete_user_pack
from app.infra.models import Pack, PackVersion, UserPack
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..types import PackError

__all__ = [
    "get_user_pack_version",
    "list_user_packs",
    "get_user_pack",
    "activate_pack_version",
    "delete_user_pack",
]


async def get_user_pack_version(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> tuple[Pack, PackVersion]:
    result = await session.execute(
        select(Pack, PackVersion)
        .join(PackVersion, PackVersion.pack_id == Pack.id)
        .join(UserPack, UserPack.pack_id == Pack.id)
        .where(
            PackVersion.id == pack_version_id,
            UserPack.user_id == user_id,
            UserPack.active.is_(True),
        ),
    )
    row = result.first()
    if row is None:
        raise PackError(404, "pack version not found")
    pack, pack_version = row
    return pack, pack_version


async def list_user_packs(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[tuple[Pack, PackVersion, datetime]]:
    result = await session.execute(
        select(Pack, PackVersion, UserPack.installed_at)
        .join(UserPack, UserPack.pack_id == Pack.id)
        .join(PackVersion, PackVersion.id == UserPack.pack_version_id)
        .where(UserPack.user_id == user_id, UserPack.active.is_(True))
        .order_by(UserPack.installed_at.desc())
    )
    return [tuple(row) for row in result.all()]


async def get_user_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> tuple[Pack, list[PackVersion], PackVersion]:
    pack = await session.get(Pack, pack_id)
    if pack is None:
        raise PackError(404, "pack not found")

    installation = await session.get(UserPack, (user_id, pack_id))
    if installation is None or not installation.active:
        raise PackError(404, "pack not found")

    versions_result = await session.execute(
        select(PackVersion)
        .where(PackVersion.pack_id == pack_id)
        .order_by(PackVersion.created_at.desc())
    )
    versions = list(versions_result.scalars())
    active = await session.get(PackVersion, installation.pack_version_id)
    if active is None:
        raise PackError(404, "pack not found")
    return pack, versions, active
