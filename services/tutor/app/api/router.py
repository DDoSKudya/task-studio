from __future__ import annotations

import uuid

from app.api.deps import ClientDep, ConfigDep, RedisDep, UserId
from app.domain.chat import build_hints, prepare_chat, stream_chat
from app.domain.studio import suggest_pack_fragment
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from studio_contracts.studio_schemas import StudioSuggestRequest, StudioSuggestResponse
from studio_contracts.tutor_schemas import TutorChatRequest, TutorHintResponse

router = APIRouter(prefix="/internal/v1/tutor", tags=["tutor"])


@router.get("/hints/{step_id}", response_model=TutorHintResponse)
async def get_hints(
    step_id: str,
    session_id: uuid.UUID,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> TutorHintResponse:
    return await build_hints(
        client,
        config,
        user_id=user_id,
        session_id=session_id,
        step_id=step_id,
    )


@router.post("/studio/suggest", response_model=StudioSuggestResponse)
async def studio_suggest(
    body: StudioSuggestRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> StudioSuggestResponse:
    return await suggest_pack_fragment(
        client,
        config,
        user_id=user_id,
        body=body,
    )


@router.post("/chat")
async def tutor_chat(
    body: TutorChatRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
    redis: RedisDep,
) -> StreamingResponse:
    context = await prepare_chat(
        client,
        redis,
        config,
        user_id=user_id,
        session_id=body.session_id,
    )
    return StreamingResponse(
        stream_chat(client, context, message=body.message),
        media_type="text/event-stream",
    )
