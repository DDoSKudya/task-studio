from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from app.domain.llm.request import chat_payload, request_headers
from app.domain.llm.sse import (
    is_role_only_chunk,
    parse_sse_error,
    parse_sse_finish_reason,
    parse_sse_line,
)
from app.domain.llm.target import LlmTarget


async def stream_chat_completion(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
    conversation_id: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    num_ctx: int | None = None,
    response_format: dict[str, str] | None = None,
    finish_reason_out: list[str | None] | None = None,
) -> AsyncIterator[str]:
    url = f"{target.base_url}/chat/completions"
    read_timeout = target.read_timeout_seconds or 600.0
    timeout = httpx.Timeout(connect=10.0, read=read_timeout, write=120.0, pool=10.0)
    last_reason: str | None = None
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
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
            response_format=response_format,
        ),
        timeout=timeout,
    ) as response:
        if response.is_error:
            await response.aread()
            raise httpx.HTTPStatusError(
                f"LLM HTTP {response.status_code}",
                request=response.request,
                response=response,
            )
        async for line in response.aiter_lines():
            if line.startswith(":"):
                yield ""
                continue
            if stream_error := parse_sse_error(line):
                raise ValueError(stream_error)
            if reason := parse_sse_finish_reason(line):
                last_reason = reason
            if chunk := parse_sse_line(line):
                yield chunk
            elif is_role_only_chunk(line):
                yield ""
    if finish_reason_out is not None:
        finish_reason_out.clear()
        finish_reason_out.append(last_reason)
