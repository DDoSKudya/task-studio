from __future__ import annotations

from typing import cast

from app.domain.llm.request import chat_payload, message_content
from app.domain.llm.target import LlmTarget


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
