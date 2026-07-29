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
