from __future__ import annotations

import uuid
from typing import Annotated

from app.api.tutor_routes.llm import router as tutor_llm_router
from app.api.upstream_stream import TUTOR_LLM_TIMEOUT, stream_response_body
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream, upstream_detail
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from studio_contracts.api.tutor_schemas import TutorChatRequest, TutorHintResponse

router = APIRouter(prefix="/v1/tutor", tags=["tutor"])
router.include_router(tutor_llm_router)

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


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
        timeout=TUTOR_LLM_TIMEOUT,
    )
    response = await client.send(request, stream=True)
    if response.is_error:
        detail = upstream_detail(response)
        status_code = response.status_code
        await response.aclose()
        raise HTTPException(status_code=status_code, detail=detail)

    return StreamingResponse(
        stream_response_body(response),
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
        timeout=TUTOR_LLM_TIMEOUT,
    )
    return parse_upstream(response, TutorHintResponse)
