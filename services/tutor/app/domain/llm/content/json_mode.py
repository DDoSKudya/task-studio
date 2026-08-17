from __future__ import annotations

import asyncio
from collections.abc import Mapping

import httpx
from app.domain.json_util.extract import extract_json_object
from app.domain.llm.target import LlmTarget
from app.domain.llm.transport.client import complete_chat_result
from app.domain.llm.transport.request import JsonSchema
from app.domain.llm.transport.result import ChatCompletionResult

_JSON_SHAPE_ATTEMPTS = 3

_JSON_OBJECT: dict[str, object] = {"type": "json_object"}

_UNSUPPORTED_JSON_MODE_MARKERS = (
    "response_format",
    "json_object",
    "json_schema",
    "unknown parameter",
    "unsupported",
    "unrecognized request argument",
    "extra inputs are not permitted",
    "invalid_request_error",
    "does not support",
)


def looks_like_unsupported_json_mode(exc: BaseException) -> bool:
    detail = str(exc).casefold()
    return any(marker in detail for marker in _UNSUPPORTED_JSON_MODE_MARKERS)


async def complete_json_chat_result(
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
    prefer_json_object: bool = True,
    json_schema: JsonSchema | Mapping[str, object] | None = None,
) -> ChatCompletionResult:
    last: ChatCompletionResult | None = None
    for attempt in range(_JSON_SHAPE_ATTEMPTS):
        if last is not None and (extract_json_object(last.content) is not None or last.truncated):
            return last
        if last is not None:
            await asyncio.sleep(min(2.0, 0.35 * (2 ** (attempt - 1))))
        last = await _complete_json_chat_result_once(
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
            prefer_json_object=prefer_json_object,
            json_schema=json_schema,
        )
    assert last is not None
    return last


async def _complete_json_chat_result_once(
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
    prefer_json_object: bool = True,
    json_schema: JsonSchema | Mapping[str, object] | None = None,
) -> ChatCompletionResult:
    if json_schema is not None:
        try:
            return await complete_chat_result(
                client,
                target,
                system_prompt=system_prompt,
                user_message=user_message,
                history=history,
                conversation_id=conversation_id,
                temperature=temperature if temperature is not None else 0.0,
                top_p=top_p,
                max_tokens=max_tokens,
                num_ctx=num_ctx,
                json_schema=json_schema,
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            if not looks_like_unsupported_json_mode(exc):
                raise
    if prefer_json_object:
        try:
            return await complete_chat_result(
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
                response_format=_JSON_OBJECT,
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            if not looks_like_unsupported_json_mode(exc):
                raise
    return await complete_chat_result(
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
    )


async def complete_json_chat_completion(
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
    json_schema: JsonSchema | Mapping[str, object] | None = None,
) -> str:
    result = await complete_json_chat_result(
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
        json_schema=json_schema,
    )
    return result.content
