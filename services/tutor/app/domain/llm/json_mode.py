from __future__ import annotations

import httpx
from app.domain.llm.client import complete_chat_result
from app.domain.llm.result import ChatCompletionResult
from app.domain.llm.target import LlmTarget

_JSON_OBJECT = {"type": "json_object"}


_UNSUPPORTED_JSON_MODE_MARKERS = (
    "response_format",
    "json_object",
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
) -> ChatCompletionResult:

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
    )
    return result.content
