from __future__ import annotations

from datetime import datetime

from app.domain.packs import UploadedPack
from app.infra.models import Pack, PackVersion
from studio_contracts.api.catalog_schemas import (
    PackDetail,
    PackSummary,
    PackUploadResponse,
    PackVersionInfo,
)
from studio_contracts.packs.pack_content import content_modules_from_manifest
from studio_contracts.packs.pack_integrity import check_pack_integrity


def pack_summary(
    pack: Pack,
    version: PackVersion,
    installed_at: datetime,
    *,
    verify_disk: bool = False,
) -> PackSummary:
    if verify_disk:
        integrity = check_pack_integrity(version.disk_path, version.manifest)
        status = integrity.status
        issues = list(integrity.issues)
    else:
        status = "ok"
        issues = []
    modules = content_modules_from_manifest(version.manifest)
    return PackSummary(
        id=pack.id,
        slug=pack.slug,
        title=pack.title,
        source=pack.source,
        external_id=pack.external_id,
        version=version.version,
        version_id=version.id,
        installed_at=installed_at,
        integrity=status,
        integrity_issues=issues,
        has_theory=modules.has_theory,
        has_video=modules.has_video,
        has_quiz=modules.has_quiz,
        has_practice=modules.has_practice,
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
    integrity = check_pack_integrity(active.disk_path, active.manifest)
    return PackDetail(
        id=pack.id,
        slug=pack.slug,
        title=pack.title,
        source=pack.source,
        external_id=pack.external_id,
        schema_version=pack.schema_version,
        active_version=pack_version_info(active, active=True),
        versions=[pack_version_info(item, active=item.id == active.id) for item in versions],
        manifest=active.manifest,
        integrity=integrity.status,
        integrity_issues=list(integrity.issues),
    )


def pack_upload_response(uploaded: UploadedPack) -> PackUploadResponse:
    return PackUploadResponse(
        pack_id=uploaded.pack_id,
        version_id=uploaded.version_id,
        slug=uploaded.slug,
        title=uploaded.title,
        version=uploaded.version,
    )
