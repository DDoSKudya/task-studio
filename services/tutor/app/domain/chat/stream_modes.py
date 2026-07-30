from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

import httpx
from app.domain.prompt_compose import format_learner_turn

from .models import (
    ChatContext,
    _complete_chat_completion,
    _iter_stream_tokens,
    _stream_ping_seconds,
)
from .ollama_polish import ollama_draft_and_polish
from .view import _sse_event


async def buffered_chat(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    message: str,
    history: list[dict[str, str]] | None,
) -> AsyncIterator[bytes]:
                                                                           
    pending = asyncio.create_task(
        ollama_draft_and_polish(
            client,
            context,
            message=message,
            history=history,
        )
    )
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=_stream_ping_seconds())
            if done:
                break
            yield _sse_event({"type": "ping"})
        content = pending.result()
        yield _sse_event({"type": "token", "content": content})
        yield _sse_event({"type": "done"})
    finally:
        if not pending.done():
            pending.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pending


async def cursor_buffered_chat(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    message: str,
    history: list[dict[str, str]] | None,
) -> AsyncIterator[bytes]:
                                                                                     
    pending = asyncio.create_task(
        _complete_chat_completion(
            client,
            context.target,
            system_prompt=context.system_prompt,
            user_message=format_learner_turn(message),
            history=history,
            conversation_id=context.conversation_id,
        )
    )
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=_stream_ping_seconds())
            if done:
                break
            yield _sse_event({"type": "ping"})
        content = pending.result()
        yield _sse_event({"type": "token", "content": content})
        yield _sse_event({"type": "done"})
    finally:
        if not pending.done():
            pending.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pending


async def token_stream_chat(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    message: str,
    history: list[dict[str, str]] | None,
) -> AsyncIterator[bytes]:
    tokens = _iter_stream_tokens(
        client,
        context.target,
        system_prompt=context.system_prompt,
        user_message=format_learner_turn(message),
        history=history,
        conversation_id=context.conversation_id,
    ).__aiter__()

    async def _next_token() -> str:
        return await anext(tokens)

    pending = asyncio.create_task(_next_token())
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=_stream_ping_seconds())
            if not done:
                yield _sse_event({"type": "ping"})
                continue
            try:
                token = pending.result()
            except StopAsyncIteration:
                break
            if token == "":
                yield _sse_event({"type": "ping"})
            else:
                yield _sse_event({"type": "token", "content": token})
            pending = asyncio.create_task(_next_token())
    finally:
        if not pending.done():
            pending.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pending
    yield _sse_event({"type": "done"})
