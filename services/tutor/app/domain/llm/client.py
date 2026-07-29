from __future__ import annotations

import httpx
from app.domain.llm.errors import llm_http_error_message
from app.domain.llm.request import (
    chat_payload,
    choice_finish_reason,
    message_content,
    request_headers,
)
from app.domain.llm.result import ChatCompletionResult
from app.domain.llm.sse import is_role_only_chunk, parse_sse_error, parse_sse_line
from app.domain.llm.stream import stream_chat_completion
from app.domain.llm.target import LlmTarget

__all__ = [
    "chat_payload",
    "complete_chat_completion",
    "complete_chat_result",
    "is_role_only_chunk",
    "llm_http_error_message",
    "message_content",
    "parse_sse_error",
    "parse_sse_line",
    "request_headers",
    "stream_chat_completion",
]


async def complete_chat_result(
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
) -> ChatCompletionResult:
    url = f"{target.base_url}/chat/completions"
    timeout = httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)
    response = await client.post(
        url,
        headers=request_headers(target, conversation_id=conversation_id),
        json=chat_payload(
            target,
            system_prompt=system_prompt,
            user_message=user_message,
            stream=False,
            history=history,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
            response_format=response_format,
        ),
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValueError(llm_http_error_message(exc)) from exc
    body = response.json()
    if not isinstance(body, dict):
        msg = "invalid LLM response"
        raise ValueError(msg)
    return ChatCompletionResult(
        content=message_content(body),
        finish_reason=choice_finish_reason(body),
        max_tokens=max_tokens,
    )


async def complete_chat_completion(
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
) -> str:
    result = await complete_chat_result(
        client,
        target,
        system_prompt=system_prompt,
        user_message=user_message,
        history=history,
        conversation_id=conversation_id,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        num_ctx=num_ctx,
        response_format=response_format,
    )
    return result.content
