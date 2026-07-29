from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from tutor_helpers.loaders import load_service_module


@pytest.mark.asyncio
async def test_ollama_buffered_chat_runs_polish(monkeypatch: pytest.MonkeyPatch) -> None:
    chat = load_service_module("app.domain.chat")
    llm = load_service_module("app.domain.llm")

    calls: list[str] = []

    async def fake_complete(
        *_args: object,
        system_prompt: str = "",
        **_kwargs: object,
    ) -> str:
        calls.append(system_prompt[:48])
        await asyncio.sleep(0.01)
        if "polish" in system_prompt.lower() or "clean tutor" in system_prompt.lower():
            return "Чистый ответ на русском без чужих языков."
        return "Draft with فقط garbage mixed in the middle."

    monkeypatch.setattr(chat, "complete_chat_completion", fake_complete)
    monkeypatch.setattr(chat, "_STREAM_PING_SECONDS", 0.01)

    context = chat.ChatContext(
        target=llm.LlmTarget("http://ollama:11434/v1", None, "llama3.2"),
        system_prompt="sys",
        conversation_id="sess",
        compact=True,
    )

    frames: list[dict[str, object]] = []
    async for raw in chat.stream_chat(object(), context, message="Почему нужен JOIN?"):
        frames.append(json.loads(raw.decode().removeprefix("data:").strip()))

    tokens = [frame["content"] for frame in frames if frame["type"] == "token"]
    assert len(calls) >= 2
    assert tokens == ["Чистый ответ на русском без чужих языков."]


@pytest.mark.asyncio
async def test_external_stream_chat_emits_ping_while_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat = load_service_module("app.domain.chat")
    llm = load_service_module("app.domain.llm")

    async def slow_tokens(*_args: object, **_kwargs: object) -> AsyncIterator[str]:
        await asyncio.sleep(0.05)
        yield "Hi"
        yield ""

    monkeypatch.setattr(chat, "stream_chat_completion", slow_tokens)
    monkeypatch.setattr(chat, "_STREAM_PING_SECONDS", 0.01)

    context = chat.ChatContext(
        target=llm.LlmTarget("https://api.mistral.ai/v1", "key", "mistral"),
        system_prompt="sys",
        conversation_id="sess",
        compact=False,
    )

    frames: list[dict[str, object]] = []
    async for raw in chat.stream_chat(object(), context, message="hello"):
        frames.append(json.loads(raw.decode().removeprefix("data:").strip()))

    types = [frame["type"] for frame in frames]
    assert "ping" in types
    assert "token" in types
    assert types[-1] == "done"
