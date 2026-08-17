from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.infra.models import UserPack
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_installation(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> None:
    installation = await session.get(UserPack, (user_id, pack_id))
    now = datetime.now(UTC)
    if installation is None:
        session.add(
            UserPack(
                user_id=user_id,
                pack_id=pack_id,
                pack_version_id=pack_version_id,
                installed_at=now,
                active=True,
            )
        )
        return

    installation.pack_version_id = pack_version_id
    installation.installed_at = now
    installation.active = True
