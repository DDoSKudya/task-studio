from __future__ import annotations

from app.api.deps import ClientDep, ConfigDep, RedisDep, UserId
from app.api.routes.learner_core import router as learner_core_router
from app.domain.chat import prepare_chat, stream_chat
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from studio_contracts.api.tutor_schemas import TutorChatRequest

router = APIRouter()
router.include_router(learner_core_router)


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
    history = [
        {"role": turn.role, "content": turn.content}
        for turn in body.history[-20:]
        if turn.content.strip()
    ]
    return StreamingResponse(
        stream_chat(client, context, message=body.message, history=history or None),
        media_type="text/event-stream",
    )
