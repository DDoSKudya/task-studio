from __future__ import annotations

from app.api.studio_routes.build import build_pack_response, validate_manifest_response
from fastapi import APIRouter
from fastapi.responses import Response
from studio_contracts.studio_schemas import (
    StudioBuildRequest,
    StudioValidateRequest,
    StudioValidateResponse,
)

router = APIRouter(prefix="/v1/studio", tags=["studio"])


@router.post("/validate", response_model=StudioValidateResponse)
async def validate_manifest(body: StudioValidateRequest) -> StudioValidateResponse:
    return validate_manifest_response(body)


@router.post("/build")
async def build_pack(body: StudioBuildRequest) -> Response:
    return build_pack_response(body)
