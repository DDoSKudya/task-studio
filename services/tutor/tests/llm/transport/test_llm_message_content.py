from __future__ import annotations

from typing import cast

from app.domain.llm.target import LlmTarget
from app.domain.llm.transport.request import chat_payload, message_content


def test_message_content_accepts_text_parts_list() -> None:
    body = cast(
        dict[str, object],
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": '{"pack_id": "demo"}'},
                        ]
                    }
                }
            ]
        },
    )
    assert message_content(body) == '{"pack_id": "demo"}'


def test_chat_payload_includes_response_format() -> None:
    target = LlmTarget("https://api.mistral.ai/v1", "key", "mistral-small")
    payload = chat_payload(
        target,
        system_prompt="sys",
        user_message="user",
        stream=False,
        response_format={"type": "json_object"},
    )
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["model"] == "mistral-small"
    assert "keep_alive" not in payload


def test_chat_payload_ollama_num_ctx_keeps_model_warm() -> None:
    target = LlmTarget("http://ollama:11434/v1", None, "qwen2.5:3b")
    payload = chat_payload(
        target,
        system_prompt="sys",
        user_message="user",
        stream=False,
        num_ctx=2048,
        max_tokens=900,
    )
    assert payload["options"] == {"num_ctx": 2048}
    assert payload["keep_alive"] == "-1"


def test_chat_payload_ollama_puts_schema_in_format() -> None:
    target = LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    schema = {
        "type": "object",
        "properties": {"chapters": {"type": "array"}},
        "required": ["chapters"],
    }
    payload = chat_payload(
        target,
        system_prompt="sys",
        user_message="user",
        stream=False,
        num_ctx=8192,
        json_schema=schema,
    )
    assert payload["format"] == schema
    assert "response_format" not in payload


def test_chat_payload_cursor_with_num_ctx_keeps_openai_schema() -> None:
    target = LlmTarget("http://cursor-proxy:8015/v1", "key", "auto", num_ctx=8192)
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    payload = chat_payload(
        target,
        system_prompt="sys",
        user_message="user",
        stream=False,
        num_ctx=8192,
        json_schema=schema,
    )
    assert "format" not in payload
    assert "options" not in payload
    assert "keep_alive" not in payload
    response_format = payload["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    response_schema = response_format["json_schema"]
    assert isinstance(response_schema, dict)
    assert response_schema["schema"] == schema


def test_chat_payload_external_schema_uses_response_format() -> None:
    target = LlmTarget("https://api.openai.com/v1", "key", "gpt-4o-mini")
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    payload = chat_payload(
        target,
        system_prompt="sys",
        user_message="user",
        stream=False,
        json_schema=schema,
    )
    assert "format" not in payload
    response_format = payload["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    response_schema = response_format["json_schema"]
    assert isinstance(response_schema, dict)
    assert response_schema["schema"] == schema
