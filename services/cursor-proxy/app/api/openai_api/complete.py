from __future__ import annotations

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.config import CursorProxyConfig
from app.domain.cursor import client as cursor_client
from app.domain.openai.format import openai_non_stream_response


async def complete_chat_non_stream(
    client: httpx.AsyncClient,
    *,
    config: CursorProxyConfig,
    api_key: str,
    prompt: str,
    model: str,
    completion_id: str,
) -> JSONResponse:
    agent_id: str | None = None
    try:
        agent_id, run_id = await cursor_client.create_chat_run(
            client,
            api_base=config.cursor_api_base,
            api_key=api_key,
            prompt=prompt,
            model=model,
            request_timeout=config.request_timeout_seconds,
        )
        content = await cursor_client.wait_for_run_result(
            client,
            api_base=config.cursor_api_base,
            api_key=api_key,
            agent_id=agent_id,
            run_id=run_id,
            request_timeout=config.request_timeout_seconds,
        )
        return JSONResponse(
            openai_non_stream_response(model=model, content=content, completion_id=completion_id)
        )
    except cursor_client.CursorApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    finally:
        if agent_id and config.cleanup_agents:
            await cursor_client.delete_agent(
                client,
                api_base=config.cursor_api_base,
                api_key=api_key,
                agent_id=agent_id,
            )
