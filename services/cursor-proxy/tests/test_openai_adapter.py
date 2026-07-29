from __future__ import annotations

from app.domain.openai.format import openai_models_payload, openai_non_stream_response
from app.domain.prompt import messages_to_prompt


def test_messages_to_prompt_includes_system_and_turns() -> None:
    prompt = messages_to_prompt(
        [
            {"role": "system", "content": "You are a tutor."},
            {"role": "user", "content": "What is JOIN?"},
            {"role": "assistant", "content": "JOIN combines tables."},
            {"role": "user", "content": "Give an example."},
        ]
    )
    assert "You are a tutor." in prompt
    assert "user: What is JOIN?" in prompt
    assert "assistant: JOIN combines tables." in prompt
    assert "Give an example." in prompt
    assert "do not run shell" in prompt.lower() or "Do not run shell" in prompt
    assert "JSON object only" not in prompt


def test_messages_to_prompt_honors_json_object_response_format() -> None:
    prompt = messages_to_prompt(
        [
            {"role": "system", "content": "Return syllabus JSON."},
            {"role": "user", "content": "Analyze this article."},
        ],
        response_format={"type": "json_object"},
    )
    assert "OUTPUT CONSTRAINT" in prompt
    assert "single JSON object only" in prompt
    assert "Return syllabus JSON." in prompt


def test_openai_models_payload_shape() -> None:
    payload = openai_models_payload(["auto", "composer-2"])
    assert payload["object"] == "list"
    assert [row["id"] for row in payload["data"]] == ["auto", "composer-2"]


def test_openai_non_stream_response_shape() -> None:
    payload = openai_non_stream_response(
        model="auto",
        content="Hello",
        completion_id="chatcmpl-test",
    )
    assert payload["id"] == "chatcmpl-test"
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["content"] == "Hello"
    assert payload["choices"][0]["finish_reason"] == "stop"
