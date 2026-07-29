from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from app.domain.llm.request import chat_payload, request_headers
from app.domain.llm.sse import is_role_only_chunk, parse_sse_error, parse_sse_line
from app.domain.llm.target import LlmTarget


async def stream_chat_completion(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
    conversation_id: str | None = None,
) -> AsyncIterator[str]:
    url = f"{target.base_url}/chat/completions"
                                                                                  
    timeout = httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)
    async with client.stream(
        "POST",
        url,
        headers=request_headers(target, conversation_id=conversation_id),
        json=chat_payload(
            target,
            system_prompt=system_prompt,
            user_message=user_message,
            stream=True,
            history=history,
        ),
        timeout=timeout,
    ) as response:
        if response.is_error:
            body = await response.aread()
            raise httpx.HTTPStatusError(
                body.decode("utf-8", errors="replace"),
                request=response.request,
                response=response,
            )
        async for line in response.aiter_lines():
            if line.startswith(":"):
                                                                                         
                yield ""
                continue
            if stream_error := parse_sse_error(line):
                raise ValueError(stream_error)
            if chunk := parse_sse_line(line):
                yield chunk
            elif is_role_only_chunk(line):
                yield ""
