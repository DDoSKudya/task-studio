from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.infra.models import Pack, PackVersion, UserPack
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.pack import ParsedManifest, extract_pack_archive, parse_manifest

from ..types import PackError, UploadedPack

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


