from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx

from app.config import CursorProxyConfig
from app.domain.cursor import client as cursor_client
from app.domain.keepalive import wait_ready_with_keepalive


async def iter_chat_run_frames(
    client: httpx.AsyncClient,
    *,
    config: CursorProxyConfig,
    api_key: str,
    prompt: str,
    model: str,
) -> AsyncIterator[bytes | tuple[str, str]]:
    create_task = asyncio.create_task(
        cursor_client.create_chat_run(
            client,
            api_base=config.cursor_api_base,
            api_key=api_key,
            prompt=prompt,
            model=model,
            request_timeout=config.request_timeout_seconds,
        )
    )
    async for frame in wait_ready_with_keepalive(create_task):
        yield frame
    agent_id, run_id = create_task.result()

    poll_task = asyncio.create_task(
        cursor_client.wait_for_run_result(
            client,
            api_base=config.cursor_api_base,
            api_key=api_key,
            agent_id=agent_id,
            run_id=run_id,
            request_timeout=config.request_timeout_seconds,
        )
    )
    async for frame in wait_ready_with_keepalive(poll_task):
        yield frame
    yield (agent_id, poll_task.result())
