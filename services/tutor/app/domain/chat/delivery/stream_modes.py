from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

import httpx
from app.domain.chat.delivery.sse import sse_event
from app.domain.chat.polish.ollama_polish import ollama_draft_and_polish
from app.domain.chat.session.models import (
    ChatContext,
    complete_bound_chat,
    iter_bound_stream_tokens,
    stream_ping_seconds,
)
from app.domain.prompt_compose import format_learner_turn


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
            done, _ = await asyncio.wait({pending}, timeout=stream_ping_seconds())
            if done:
                break
            yield sse_event({"type": "ping"})
        content = pending.result()
        yield sse_event({"type": "token", "content": content})
        yield sse_event({"type": "done"})
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
        complete_bound_chat(
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
            done, _ = await asyncio.wait({pending}, timeout=stream_ping_seconds())
            if done:
                break
            yield sse_event({"type": "ping"})
        content = pending.result()
        yield sse_event({"type": "token", "content": content})
        yield sse_event({"type": "done"})
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
    tokens = iter_bound_stream_tokens(
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
            done, _ = await asyncio.wait({pending}, timeout=stream_ping_seconds())
            if not done:
                yield sse_event({"type": "ping"})
                continue
            try:
                token = pending.result()
            except StopAsyncIteration:
                break
            if token == "":
                yield sse_event({"type": "ping"})
            else:
                yield sse_event({"type": "token", "content": token})
            pending = asyncio.create_task(_next_token())
    finally:
        if not pending.done():
            pending.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pending
    yield sse_event({"type": "done"})
