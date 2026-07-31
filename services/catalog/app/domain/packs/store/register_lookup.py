from __future__ import annotations

import uuid

from app.infra.models import Pack
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.pack import ParsedManifest


async def get_or_create_imported_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedManifest,
    *,
    external_id: str,
    source: str,
) -> Pack:
    pack: Pack | None = None
    if external_id:
        by_external = await session.execute(
            select(Pack).where(
                Pack.owner_user_id == user_id,
                Pack.source == source,
                Pack.external_id == external_id,
            ),
        )
        pack = by_external.scalar_one_or_none()
    if pack is None:
        by_slug = await session.execute(
            select(Pack).where(Pack.owner_user_id == user_id, Pack.slug == parsed.slug),
        )
        pack = by_slug.scalar_one_or_none()
    if pack is None:
        pack = Pack(
            owner_user_id=user_id,
            slug=parsed.slug,
            title=parsed.title,
            source=source,
            external_id=external_id,
            schema_version=parsed.schema_version,
        )
        session.add(pack)
        await session.flush()
        return pack

    if pack.slug != parsed.slug:
        slug_taken = await session.execute(
            select(Pack).where(
                Pack.owner_user_id == user_id,
                Pack.slug == parsed.slug,
                Pack.id != pack.id,
            ),
        )
        if slug_taken.scalar_one_or_none() is None:
            pack.slug = parsed.slug
    pack.title = parsed.title
    pack.source = source
    pack.external_id = external_id
    pack.schema_version = parsed.schema_version
    return pack
