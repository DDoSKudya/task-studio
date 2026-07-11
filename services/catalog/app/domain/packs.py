from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.infra.models import Pack, PackVersion, UserPack
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.pack import ParsedManifest, extract_pack_archive


class PackError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class UploadedPack:
    pack_id: uuid.UUID
    version_id: uuid.UUID
    slug: str
    title: str
    version: str


async def upload_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    archive: bytes,
    *,
    packs_root: Path,
    max_upload_bytes: int,
) -> UploadedPack:
    if len(archive) > max_upload_bytes:
        raise PackError(413, "pack exceeds upload limit")

    pack_dir = packs_root / str(user_id)
    pack_dir.mkdir(parents=True, exist_ok=True)
    staging = pack_dir / f".upload-{uuid.uuid4()}"
    staging.mkdir(parents=True, exist_ok=True)

    try:
        parsed = extract_pack_archive(archive, staging)
    except (ValueError, OSError) as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise PackError(422, str(exc)) from exc

    pack = await _get_or_create_pack(session, user_id, parsed)
    await _reject_duplicate_version(session, pack.id, parsed.version, staging)

    final_path = pack_dir / str(pack.id) / parsed.version
    if final_path.exists():
        shutil.rmtree(final_path)
    staging.rename(final_path)

    pack_version = await _persist_pack_version(
        session,
        user_id,
        pack,
        parsed,
        final_path,
    )
    return UploadedPack(
        pack_id=pack.id,
        version_id=pack_version.id,
        slug=parsed.slug,
        title=parsed.title,
        version=parsed.version,
    )


async def _get_or_create_pack(
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


async def _reject_duplicate_version(
    session: AsyncSession,
    pack_id: uuid.UUID,
    version: str,
    staging: Path,
) -> None:
    existing = await session.execute(
        select(PackVersion).where(PackVersion.pack_id == pack_id, PackVersion.version == version),
    )
    if existing.scalar_one_or_none() is not None:
        shutil.rmtree(staging, ignore_errors=True)
        raise PackError(409, "pack version already exists")


async def _persist_pack_version(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack: Pack,
    parsed: ParsedManifest,
    final_path: Path,
) -> PackVersion:
    pack_version = PackVersion(
        pack_id=pack.id,
        version=parsed.version,
        manifest=parsed.raw,
        disk_path=str(final_path),
    )
    session.add(pack_version)
    await session.flush()
    await _upsert_installation(session, user_id, pack.id, pack_version.id)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        shutil.rmtree(final_path, ignore_errors=True)
        raise PackError(422, "pack could not be saved") from exc

    return pack_version


async def _upsert_installation(
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


async def delete_user_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    *,
    packs_root: Path,
) -> None:
    pack = await session.get(Pack, pack_id)
    if pack is None or pack.owner_user_id != user_id:
        raise PackError(404, "pack not found")

    installation = await session.get(UserPack, (user_id, pack_id))
    if installation is None:
        raise PackError(404, "pack not found")

    versions_result = await session.execute(
        select(PackVersion).where(PackVersion.pack_id == pack_id),
    )
    disk_paths = [pack_version.disk_path for pack_version in versions_result.scalars()]

    await session.delete(installation)
    await session.delete(pack)
    await session.commit()

    for disk_path in disk_paths:
        shutil.rmtree(disk_path, ignore_errors=True)
    shutil.rmtree(packs_root / str(user_id) / str(pack_id), ignore_errors=True)
