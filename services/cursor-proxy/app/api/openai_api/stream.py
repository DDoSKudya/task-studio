from __future__ import annotations

import time

import httpx
import structlog

from app.api.openai_api.stream_run import iter_chat_run_frames
from app.config import CursorProxyConfig
from app.domain import cursor_client
from app.domain.openai.sse import (
    chunk_text,
    openai_content_chunk,
    openai_error_chunk,
    openai_role_chunk,
    openai_stop_chunk,
)

log = structlog.get_logger("cursor-proxy.openai")


async def stream_chat(
    client: httpx.AsyncClient,
    *,
    config: CursorProxyConfig,
    api_key: str,
    prompt: str,
    model: str,
    completion_id: str,
):
    created = int(time.time())
    yield openai_role_chunk(model=model, completion_id=completion_id, created=created).encode()

    agent_id: str | None = None
    try:
        content = ""
        async for item in iter_chat_run_frames(
            client,
            config=config,
            api_key=api_key,
            prompt=prompt,
            model=model,
        ):
            if isinstance(item, tuple):
                agent_id, content = item
                continue
            yield item

        for piece in chunk_text(content):
            yield openai_content_chunk(
                model=model,
                completion_id=completion_id,
                created=created,
                text=piece,
            ).encode()
        yield openai_stop_chunk(model=model, completion_id=completion_id, created=created).encode()
        yield b"data: [DONE]\n\n"
        log.info("cursor_chat_completed", agent_id=agent_id, chars=len(content))
    except cursor_client.CursorApiError as exc:
        yield openai_error_chunk(exc.detail, code=exc.status_code).encode()
        yield b"data: [DONE]\n\n"
    except httpx.TimeoutException:
        yield openai_error_chunk(
            "Cursor API timed out while waiting for the cloud agent.",
            code=504,
        ).encode()
        yield b"data: [DONE]\n\n"
    except Exception as exc:  # noqa: BLE001 - boundary of SSE generator
        log.exception("cursor_chat_failed", error=exc.__class__.__name__)
        yield openai_error_chunk(
            f"cursor-proxy failure: {exc.__class__.__name__}",
            code=502,
        ).encode()
        yield b"data: [DONE]\n\n"
    finally:
        if agent_id and config.cleanup_agents:
            await cursor_client.delete_agent(
                client,
                api_base=config.cursor_api_base,
                api_key=api_key,
                agent_id=agent_id,
            )
