from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream, upstream_detail
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from studio_contracts.tutor_schemas import TutorChatRequest, TutorHintResponse

router = APIRouter(prefix="/v1/tutor", tags=["tutor"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


async def _stream_response_body(response: httpx.Response) -> AsyncIterator[bytes]:
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    finally:
        await response.aclose()


@router.post("/chat")
async def tutor_chat(
    body: TutorChatRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> StreamingResponse:
    url = f"{settings.tutor_service_url}/internal/v1/tutor/chat"
    request = client.build_request(
        "POST",
        url,
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
    )
    response = await client.send(request, stream=True)
    if response.is_error:
        detail = upstream_detail(response)
        status_code = response.status_code
        await response.aclose()
        raise HTTPException(status_code=status_code, detail=detail)

    return StreamingResponse(
        _stream_response_body(response),
        media_type="text/event-stream",
    )


@router.get("/hints/{step_id}", response_model=TutorHintResponse)
async def tutor_hints(
    step_id: str,
    session_id: Annotated[uuid.UUID, Query()],
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> TutorHintResponse:
    response = await client.get(
        f"{settings.tutor_service_url}/internal/v1/tutor/hints/{step_id}",
        headers={"X-User-Id": str(user_id)},
        params={"session_id": str(session_id)},
    )
    return parse_upstream(response, TutorHintResponse)
