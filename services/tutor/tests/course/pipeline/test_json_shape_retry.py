from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from tutor_helpers.loaders import load_service_module


@pytest.mark.asyncio
async def test_complete_json_chat_result_retries_prose_then_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_mode = load_service_module("app.domain.llm.content.json_mode")
    from app.domain.llm.transport.result import ChatCompletionResult

    contents = ["Sure, here you go.", '{"ok": true}']

    async def fake_once(*_args: object, **_kwargs: object) -> ChatCompletionResult:
        return ChatCompletionResult(
            content=contents.pop(0),
            finish_reason="stop",
            max_tokens=100,
        )

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(json_mode, "_complete_json_chat_result_once", fake_once)
    monkeypatch.setattr(json_mode.asyncio, "sleep", no_sleep)
    result = await json_mode.complete_json_chat_result(
        AsyncMock(),
        SimpleNamespace(),
        system_prompt="s",
        user_message="u",
    )
    assert result.content == '{"ok": true}'
    assert contents == []


@pytest.mark.asyncio
async def test_complete_json_chat_result_keeps_valid_object_on_first_try(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_mode = load_service_module("app.domain.llm.content.json_mode")
    from app.domain.llm.transport.result import ChatCompletionResult

    calls = {"n": 0}

    async def fake_once(*_args: object, **_kwargs: object) -> ChatCompletionResult:
        calls["n"] += 1
        return ChatCompletionResult(
            content='{"title": "ok"}',
            finish_reason="stop",
            max_tokens=100,
        )

    monkeypatch.setattr(json_mode, "_complete_json_chat_result_once", fake_once)
    result = await json_mode.complete_json_chat_result(
        AsyncMock(),
        SimpleNamespace(),
        system_prompt="s",
        user_message="u",
    )
    assert result.content == '{"title": "ok"}'
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_complete_json_raw_until_done_does_not_continue_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cont = load_service_module("app.domain.llm.content.continue_text")
    from app.domain.llm.target import LlmTarget
    from app.domain.llm.transport.result import ChatCompletionResult

    async def fake_json(*_args: object, **_kwargs: object) -> ChatCompletionResult:
        return ChatCompletionResult(content="", finish_reason="stop", max_tokens=100)

    async def boom(*_args: object, **_kwargs: object) -> ChatCompletionResult:
        raise AssertionError("must not continue empty JSON")

    monkeypatch.setattr("app.domain.llm.content.json_mode.complete_json_chat_result", fake_json)
    monkeypatch.setattr(cont, "complete_chat_result", boom)
    result = await cont.complete_json_raw_until_done(
        AsyncMock(),
        LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
        system_prompt="s",
        user_message="u",
        max_tokens=200,
    )
    assert result.content == ""


@pytest.mark.asyncio
async def test_complete_json_raw_until_done_does_not_continue_closed_prose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cont = load_service_module("app.domain.llm.content.continue_text")
    from app.domain.llm.target import LlmTarget
    from app.domain.llm.transport.result import ChatCompletionResult

    async def fake_json(*_args: object, **_kwargs: object) -> ChatCompletionResult:
        return ChatCompletionResult(
            content="I cannot produce JSON.",
            finish_reason="stop",
            max_tokens=100,
        )

    async def boom(*_args: object, **_kwargs: object) -> ChatCompletionResult:
        raise AssertionError("must not continue closed prose as JSON")

    monkeypatch.setattr("app.domain.llm.content.json_mode.complete_json_chat_result", fake_json)
    monkeypatch.setattr(cont, "complete_chat_result", boom)
    result = await cont.complete_json_raw_until_done(
        AsyncMock(),
        LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
        system_prompt="s",
        user_message="u",
        max_tokens=200,
    )
    assert "cannot produce" in result.content


@pytest.mark.asyncio
async def test_load_json_object_extracts_wrapped_payload() -> None:
    schemas = load_service_module("app.domain.course_from_article.local_course.policy.schemas")
    parsed = await schemas.load_json_object(
        AsyncMock(),
        SimpleNamespace(num_ctx=8192),
        'Here is the batch:\n{"quizzes": [{"question": "Q"}]}\n',
        hint="quiz batch",
    )
    assert parsed["quizzes"][0]["question"] == "Q"


@pytest.mark.asyncio
async def test_load_json_object_repairs_when_extract_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schemas = load_service_module("app.domain.course_from_article.local_course.policy.schemas")

    async def fake_parse(*_args: object, raw: str, **_kwargs: object) -> dict[str, object] | None:
        if "fixed" in raw:
            return {"title": "fixed"}
        return {"title": "repaired"}

    monkeypatch.setattr("app.domain.json_util.repair.parse_or_repair_json", fake_parse)
    parsed = await schemas.load_json_object(
        AsyncMock(),
        SimpleNamespace(num_ctx=8192),
        "not json at all",
        hint="practice batch",
    )
    assert parsed["title"] == "repaired"


@pytest.mark.asyncio
async def test_generate_quizzes_retries_invalid_json_error() -> None:
    quiz_mod = load_service_module("app.domain.course_from_article.practice.quiz_generate")
    from studio_contracts.api.studio_schemas import CourseFromArticleRequest

    body = CourseFromArticleRequest(
        article="Path helps with files. " * 20,
        title="Path",
        locale="ru",
        quiz_count=1,
    )
    attempts = {"n": 0}

    async def fake_stage_json(*_args: object, **_kwargs: object) -> dict[str, object]:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise quiz_mod.TutorError(502, "course stage quizzes returned invalid JSON")
        return {
            "quiz": {
                "id": "quiz-1",
                "title": "Ok",
                "question": "What does Path provide for joining filesystem path parts?",
                "choices": [
                    "Join path parts safely",
                    "Only print the CWD",
                    "Delete files by default",
                    "Ignore path separators",
                ],
                "answer": 0,
            }
        }

    with patch.object(quiz_mod, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)):
        quizzes = await quiz_mod.generate_quizzes(
            AsyncMock(),
            object(),
            body=body,
            compact=True,
            chapters=[{"id": "c1", "title": "Intro", "source_excerpt": "x"}],
            outcomes=["use Path"],
            theory_steps=[{"title": "Intro", "content": "Path wraps paths."}],
        )

    assert attempts["n"] == 2
    assert quizzes[0]["id"] == "quiz-1"
