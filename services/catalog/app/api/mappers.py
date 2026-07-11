from __future__ import annotations

from datetime import datetime

from app.domain.packs import UploadedPack
from app.infra.models import Pack, PackVersion
from studio_contracts.catalog_schemas import (
    PackDetail,
    PackSummary,
    PackUploadResponse,
    PackVersionInfo,
)


def pack_summary(
    pack: Pack,
    version: PackVersion,
    installed_at: datetime,
) -> PackSummary:
    return PackSummary(
        id=pack.id,
        slug=pack.slug,
        title=pack.title,
        source=pack.source,
        version=version.version,
        version_id=version.id,
        installed_at=installed_at,
    )


def pack_version_info(version: PackVersion, *, active: bool) -> PackVersionInfo:
    return PackVersionInfo(
        id=version.id,
        version=version.version,
        created_at=version.created_at,
        active=active,
    )


def pack_detail(
    pack: Pack,
    versions: list[PackVersion],
    active: PackVersion,
) -> PackDetail:
    return PackDetail(
        id=pack.id,
        slug=pack.slug,
        title=pack.title,
        source=pack.source,
        schema_version=pack.schema_version,
        active_version=pack_version_info(active, active=True),
        versions=[pack_version_info(item, active=item.id == active.id) for item in versions],
        manifest=active.manifest,
    )


def pack_upload_response(uploaded: UploadedPack) -> PackUploadResponse:
    return PackUploadResponse(
        pack_id=uploaded.pack_id,
        version_id=uploaded.version_id,
        slug=uploaded.slug,
        title=uploaded.title,
        version=uploaded.version,
    )
