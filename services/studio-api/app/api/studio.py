from __future__ import annotations

from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from studio_contracts.pack import (
    build_pack_archive,
    collect_manifest_errors,
    decode_build_assets,
)
from studio_contracts.studio_schemas import (
    StudioBuildRequest,
    StudioSuggestRequest,
    StudioSuggestResponse,
    StudioValidateRequest,
    StudioValidateResponse,
    StudioValidationIssue,
)

router = APIRouter(prefix="/v1/studio", tags=["studio"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.post("/validate", response_model=StudioValidateResponse)
async def validate_manifest(body: StudioValidateRequest) -> StudioValidateResponse:
    issues = collect_manifest_errors(body.manifest)
    return StudioValidateResponse(
        valid=not issues,
        errors=[StudioValidationIssue(path=issue.path, message=issue.message) for issue in issues],
    )


@router.post("/build")
async def build_pack(body: StudioBuildRequest) -> Response:
    try:
        assets = decode_build_assets([(asset.path, asset.content_base64) for asset in body.assets])
        archive = build_pack_archive(body.manifest, assets)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    filename = _pack_filename(body.manifest)
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/ai/suggest", response_model=StudioSuggestResponse)
async def suggest_manifest(
    body: StudioSuggestRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> StudioSuggestResponse:
    response = await client.post(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/suggest",
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
        timeout=120.0,
    )
    return parse_upstream(response, StudioSuggestResponse)


def _pack_filename(manifest: dict[str, object]) -> str:
    slug = manifest.get("id")
    version = manifest.get("version")
    safe_slug = slug if isinstance(slug, str) and slug else "pack"
    safe_version = version if isinstance(version, str) and version else "1.0.0"
    return f"{safe_slug}-{safe_version}.studio-pack"
