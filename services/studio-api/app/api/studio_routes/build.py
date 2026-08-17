from __future__ import annotations

from fastapi import HTTPException, Response
from studio_contracts.api.studio_schemas import (
    StudioBuildRequest,
    StudioValidateRequest,
    StudioValidateResponse,
    StudioValidationIssue,
)
from studio_contracts.packs.pack import (
    build_pack_archive,
    collect_manifest_errors,
    decode_build_assets,
)


def validate_manifest_response(body: StudioValidateRequest) -> StudioValidateResponse:
    issues = collect_manifest_errors(body.manifest)
    return StudioValidateResponse(
        valid=not issues,
        errors=[StudioValidationIssue(path=issue.path, message=issue.message) for issue in issues],
    )


def build_pack_response(body: StudioBuildRequest) -> Response:
    try:
        assets = decode_build_assets([(asset.path, asset.content_base64) for asset in body.assets])
        archive = build_pack_archive(body.manifest, assets)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    filename = pack_filename(body.manifest)
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def pack_filename(manifest: dict[str, object]) -> str:
    slug = manifest.get("id")
    version = manifest.get("version")
    safe_slug = slug if isinstance(slug, str) and slug else "pack"
    safe_version = version if isinstance(version, str) and version else "1.0.0"
    return f"{safe_slug}-{safe_version}.studio-pack"
