from __future__ import annotations

from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream
from fastapi import APIRouter, Depends
from studio_contracts.api.tutor_schemas import (
    TutorLlmStatus,
    TutorLlmTestRequest,
    TutorWarmupRequest,
    TutorWarmupResponse,
)

router = APIRouter()

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/llm-status", response_model=TutorLlmStatus)
async def tutor_llm_status(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    ensure: bool = False,
) -> TutorLlmStatus:
    params = {"ensure": "true"} if ensure else None
    response = await client.get(
        f"{settings.tutor_service_url}/internal/v1/tutor/llm-status",
        headers={"X-User-Id": str(user_id)},
        params=params,
    )
    return parse_upstream(response, TutorLlmStatus)


@router.post("/warmup", response_model=TutorWarmupResponse)
async def tutor_warmup(
    body: TutorWarmupRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> TutorWarmupResponse:
    response = await client.post(
        f"{settings.tutor_service_url}/internal/v1/tutor/warmup",
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(response, TutorWarmupResponse)


@router.post("/llm-test", response_model=TutorLlmStatus)
async def tutor_llm_test(
    body: TutorLlmTestRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> TutorLlmStatus:
    response = await client.post(
        f"{settings.tutor_service_url}/internal/v1/tutor/llm-test",
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(response, TutorLlmStatus)
