from __future__ import annotations

import asyncio
from typing import Annotated

import httpx
from app.api.deps import Adapters, Settings
from app.api.routes.common.helpers import require_adapter
from app.api.routes.discovery.discover_helpers import http_client
from app.domain.credentials import fetch_platform_credentials
from fastapi import APIRouter, Depends, HTTPException, status
from studio_common.security.internal import InternalUserId
from studio_contracts.api.integration_schemas import EnrollCourseRequest, EnrollCourseResponse

router = APIRouter()

type HttpClient = Annotated[httpx.AsyncClient, Depends(http_client)]


@router.post(
    "/{platform_id}/enroll",
    response_model=EnrollCourseResponse,
    status_code=status.HTTP_200_OK,
)
async def enroll_course(
    platform_id: str,
    body: EnrollCourseRequest,
    user_id: InternalUserId,
    settings: Settings,
    adapters: Adapters,
    client: HttpClient,
) -> EnrollCourseResponse:
    adapter = require_adapter(adapters, platform_id)
    if adapter.enroll is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"platform {platform_id} does not support enroll",
        )

    credentials = await fetch_platform_credentials(
        client,
        auth_service_url=settings.auth_service_url,
        user_id=user_id,
        platform_id=platform_id,
    )

    try:
        raw = await asyncio.to_thread(
            adapter.enroll,
            course_id=body.course_id,
            **credentials,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except TypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"enroll failed: {exc}",
        ) from exc

    if not isinstance(raw, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="invalid enroll response from adapter",
        )
    return EnrollCourseResponse.model_validate(raw)
