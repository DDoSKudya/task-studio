from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from app.domain.llm import is_cursor_target
from app.domain.prompt_compose import context_budget

from .models import ChatContext
from .stream_modes import buffered_chat, cursor_buffered_chat, token_stream_chat
from .view import _provider_error_message, _sse_event

_buffered_chat = buffered_chat
_cursor_buffered_chat = cursor_buffered_chat
_token_stream_chat = token_stream_chat


async def stream_chat(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    message: str,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[bytes]:
    trimmed_history = history
    if context.compact and history:
        budget = context_budget(compact=True)
        if len(history) > budget.history_messages:
            trimmed_history = history[-budget.history_messages :]
    try:
        if context.compact:
            async for frame in buffered_chat(
                client,
                context,
                message=message,
                history=trimmed_history,
            ):
                yield frame
            return
        if is_cursor_target(context.target):
            async for frame in cursor_buffered_chat(
                client,
                context,
                message=message,
                history=trimmed_history,
            ):
                yield frame
            return
        async for frame in token_stream_chat(
            client,
            context,
            message=message,
            history=trimmed_history,
        ):
            yield frame
    except (httpx.HTTPError, ValueError) as exc:
        yield _sse_event(
            {
                "type": "error",
                "content": _provider_error_message(exc),
            }
        )
        yield _sse_event({"type": "done"})
