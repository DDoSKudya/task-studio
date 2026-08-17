from __future__ import annotations

import asyncio
from collections.abc import Mapping

import httpx
from app.domain.llm.errors import llm_http_error_message
from app.domain.llm.target import LlmTarget
from app.domain.llm.transport.request import (
    JsonSchema,
    chat_payload,
    choice_finish_reason,
    message_content,
    request_headers,
)
from app.domain.llm.transport.result import ChatCompletionResult
from app.domain.llm.transport.retry import (
    is_transient_llm_error,
    retry_delay_seconds,
    with_llm_retry,
)
from app.domain.llm.transport.sse import is_role_only_chunk, parse_sse_error, parse_sse_line
from app.domain.llm.transport.stream import stream_chat_completion

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


def _use_stream_for_cancel(target: LlmTarget) -> bool:
    return target.num_ctx is not None or "ollama" in target.base_url.casefold()


async def _complete_chat_result_stream(
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
    response_format: Mapping[str, object] | None = None,
    json_schema: JsonSchema | None = None,
) -> ChatCompletionResult:
    parts: list[str] = []
    finish_slot: list[str | None] = []
    async for chunk in stream_chat_completion(
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
        json_schema=json_schema,
        finish_reason_out=finish_slot,
    ):
        if chunk:
            parts.append(chunk)
    if not (content := "".join(parts).strip()):
        msg = "empty LLM content"
        raise ValueError(msg)
    finish_reason = finish_slot[0] if finish_slot else None
    return ChatCompletionResult(
        content=content,
        finish_reason=finish_reason,
        max_tokens=max_tokens,
    )


def _default_request_retries(target: LlmTarget) -> int:
    return max(0, target.request_retries) if target.request_retries is not None else 8


async def _complete_chat_result_nonstream(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]] | None,
    conversation_id: str | None,
    temperature: float | None,
    top_p: float | None,
    max_tokens: int | None,
    num_ctx: int | None,
    response_format: Mapping[str, object] | None,
    json_schema: JsonSchema | None,
    retries: int,
) -> ChatCompletionResult:
    url = f"{target.base_url}/chat/completions"
    read_timeout = target.read_timeout_seconds or 600.0
    timeout = httpx.Timeout(connect=10.0, read=read_timeout, write=120.0, pool=10.0)

    async def post_once(max_tokens_override: int | None) -> ChatCompletionResult:
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
                max_tokens=max_tokens_override,
                num_ctx=num_ctx,
                response_format=response_format,
                json_schema=json_schema,
            ),
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("invalid LLM response")
        return ChatCompletionResult(
            content=message_content(body),
            finish_reason=choice_finish_reason(body),
            max_tokens=max_tokens_override,
        )

    def max_tokens_for_attempt(*, attempt: int, rate_limited: bool) -> int | None:
        if max_tokens is None:
            return None
        if not rate_limited or attempt <= 0:
            return max_tokens
        reduced = int(max_tokens * (0.9**attempt))
        min_budget = max(256, int(max_tokens * 0.5))
        return max(reduced, min_budget)

    attempt = 0
    rate_limited = False
    while True:
        budget = max_tokens_for_attempt(attempt=attempt, rate_limited=rate_limited)
        try:
            return await post_once(budget)
        except asyncio.CancelledError:
            raise
        except httpx.HTTPStatusError as exc:
            if attempt >= retries or not is_transient_llm_error(exc):
                raise ValueError(llm_http_error_message(exc)) from exc
            rate_limited = exc.response.status_code == 429
            delay = retry_delay_seconds(
                exc,
                attempt=attempt,
                base_delay_seconds=3.0 if rate_limited else 2.0,
                max_delay_seconds=180.0 if rate_limited else 90.0,
            )
            await asyncio.sleep(delay)
            attempt += 1
        except httpx.HTTPError as exc:
            if attempt >= retries or not is_transient_llm_error(exc):
                raise
            rate_limited = False
            delay = retry_delay_seconds(
                exc,
                attempt=attempt,
                base_delay_seconds=2.0,
                max_delay_seconds=90.0,
            )
            await asyncio.sleep(delay)
            attempt += 1


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
    response_format: Mapping[str, object] | None = None,
    json_schema: JsonSchema | None = None,
) -> ChatCompletionResult:
    retries = _default_request_retries(target)
    if _use_stream_for_cancel(target):

        async def _stream_once() -> ChatCompletionResult:
            return await _complete_chat_result_stream(
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
                json_schema=json_schema,
            )

        try:
            return await with_llm_retry(_stream_once, retries=retries)
        except httpx.HTTPStatusError as exc:
            raise ValueError(llm_http_error_message(exc)) from exc

    return await _complete_chat_result_nonstream(
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
        json_schema=json_schema,
        retries=retries,
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
    response_format: Mapping[str, object] | None = None,
    json_schema: JsonSchema | None = None,
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
        json_schema=json_schema,
    )
    return result.content
