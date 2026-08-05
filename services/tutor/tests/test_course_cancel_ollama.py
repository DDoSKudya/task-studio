from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tutor_helpers.loaders import load_service_module


@pytest.mark.asyncio
async def test_stop_ollama_posts_keep_alive_zero() -> None:
    stop = load_service_module("app.domain.ollama.stop")
    client = AsyncMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=response)

    await stop.stop_ollama_model(
        client,
        ollama_url="http://ollama:11434",
        model="qwen2.5:7b",
    )

    client.post.assert_awaited_once()
    url = client.post.await_args.args[0]
    payload = client.post.await_args.kwargs["json"]
    assert url == "http://ollama:11434/api/generate"
    assert payload["model"] == "qwen2.5:7b"
    assert payload["keep_alive"] == 0
    assert payload["prompt"] == ""


def test_use_stream_for_cancel_on_ollama_targets() -> None:
    client_mod = load_service_module("app.domain.llm.client")
    target_mod = load_service_module("app.domain.llm.target")
    ollama = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen", num_ctx=4096)
    by_ctx = target_mod.LlmTarget("http://127.0.0.1:11434/v1", None, "qwen", num_ctx=8192)
    cloud = target_mod.LlmTarget("https://api.mistral.ai/v1", "key", "mistral")

    assert client_mod._use_stream_for_cancel(ollama) is True
    assert client_mod._use_stream_for_cancel(by_ctx) is True
    assert client_mod._use_stream_for_cancel(cloud) is False


@pytest.mark.asyncio
async def test_complete_chat_result_streams_for_ollama() -> None:
    client_mod = load_service_module("app.domain.llm.client")
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen", num_ctx=4096)

    async def fake_stream(*_args, **_kwargs):
        yield "hel"
        yield "lo"

    with patch.object(client_mod, "stream_chat_completion", fake_stream):
        result = await client_mod.complete_chat_result(
            AsyncMock(),
            target,
            system_prompt="sys",
            user_message="hi",
        )

    assert result.content == "hello"
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_keepalive_cancel_aborts_inner_generator() -> None:
    keep = load_service_module("app.domain.course_from_article.stream_keepalive")
    cancelled = asyncio.Event()

    async def slow_events():
        try:
            await asyncio.sleep(60)
            yield {"type": "done", "progress": 1.0, "message": "ok"}
        except asyncio.CancelledError:
            cancelled.set()
            raise

    with patch.object(keep, "_COURSE_STREAM_PING_SECONDS", 30.0):
        stream = keep.iter_course_sse_with_pings(slow_events())
        task = asyncio.create_task(anext(stream))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(cancelled.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_iter_course_cancel_unloads_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    pipe = load_service_module("app.domain.course_from_article.pipeline")
    stop = load_service_module("app.domain.ollama.stop")
    stopped: list[str] = []
    paused: list[dict[str, object]] = []

    async def fake_stop(_client, *, ollama_url: str, model: str) -> None:
        stopped.append(model)
        assert ollama_url == "http://ollama:11434"

    async def hanging_body(
        _client,
        _config,
        *,
        user_id,
        body,
        store,
        build_meta,
        resumed,
        active_model,
    ):
        del user_id, body, store, resumed
        active_model.clear()
        active_model.append("course-model")
        yield {
            "type": "stage",
            "stage": "analyze",
            "status": "running",
            "progress": 0.1,
            "message": str(build_meta.build_id),
        }
        await asyncio.sleep(60)

    build_id = uuid.uuid4()
    meta = SimpleNamespace(build_id=str(build_id))
    store = MagicMock()
    body = SimpleNamespace()
    config = SimpleNamespace(ollama_url="http://ollama:11434", ollama_model="fallback")

    monkeypatch.setattr(
        pipe,
        "resolve_build_session",
        lambda *_a, **_k: (store, meta, body, False),
    )
    monkeypatch.setattr(pipe, "_iter_course_from_article_body", hanging_body)
    monkeypatch.setattr(
        pipe,
        "mark_build_paused",
        lambda *_a, **kwargs: paused.append(kwargs),
    )
    monkeypatch.setattr(pipe, "sync_progress_from_event", lambda *_a, **_k: None)
    monkeypatch.setattr(stop, "stop_ollama_model", fake_stop)

    agen = pipe.iter_course_from_article(
        AsyncMock(),
        config,
        user_id=uuid.uuid4(),
        body=body,
    )
    task = asyncio.create_task(anext(agen))
    first = await asyncio.wait_for(task, timeout=1.0)
    assert first["type"] == "stage"

    waiter = asyncio.create_task(anext(agen))
    await asyncio.sleep(0.05)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter

    assert stopped == ["course-model"]
    assert paused
    assert paused[-1].get("failed") is False
    assert "Cancel" in str(paused[-1].get("message") or "")
