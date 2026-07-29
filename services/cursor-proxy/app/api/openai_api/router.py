from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.openai_api.complete import complete_chat_non_stream
from app.api.openai_api.deps import proxy_config, proxy_http, require_bearer_api_key
from app.api.openai_api.stream import stream_chat
from app.domain.cursor import client as cursor_client
from app.domain.openai.format import openai_completion_id, openai_models_payload
from app.domain.prompt import messages_to_prompt

router = APIRouter()


@router.get("/models")
async def list_models(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    api_key = require_bearer_api_key(authorization)
    config = proxy_config(request)
    client = proxy_http(request)
    try:
        model_ids = await cursor_client.list_models(
            client,
            api_base=config.cursor_api_base,
            api_key=api_key,
        )
    except cursor_client.CursorApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return openai_models_payload(model_ids)


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: Request,
    body: dict[str, Any],
    authorization: Annotated[str | None, Header()] = None,
    x_task_studio_conversation_id: Annotated[str | None, Header()] = None,
) -> StreamingResponse | JSONResponse:
    _ = x_task_studio_conversation_id
    api_key = require_bearer_api_key(authorization)
    config = proxy_config(request)
    client = proxy_http(request)

    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty array")

    model_raw = body.get("model")
    model = model_raw.strip() if isinstance(model_raw, str) and model_raw.strip() else "auto"
    stream = bool(body.get("stream"))
    completion_id = openai_completion_id()
    prompt = messages_to_prompt(messages, response_format=body.get("response_format"))

    if stream:
        return StreamingResponse(
            stream_chat(
                client,
                config=config,
                api_key=api_key,
                prompt=prompt,
                model=model,
                completion_id=completion_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    return await complete_chat_non_stream(
        client,
        config=config,
        api_key=api_key,
        prompt=prompt,
        model=model,
        completion_id=completion_id,
    )
