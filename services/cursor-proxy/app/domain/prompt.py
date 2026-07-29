from __future__ import annotations

from typing import Any

_CHAT_PREAMBLE = """You are an OpenAI-compatible chat completions backend for Task Studio.
Answer as the assistant in a normal chat. Reply with the answer text only.
Do not edit files, do not run shell commands, do not call tools, and do not create PRs.
If course or page context is in a system message, treat that as authoritative.
"""

_JSON_OBJECT_CONSTRAINT = """OUTPUT CONSTRAINT:
Return ONE valid JSON object only.
No markdown fences, no commentary, no preamble, no trailing text.
Do not edit files, do not run shell commands, and do not call tools.
"""


def is_json_object_format(response_format: object) -> bool:
    if not isinstance(response_format, dict):
        return False
    kind = response_format.get("type")
    return isinstance(kind, str) and kind.strip().casefold() == "json_object"


def messages_to_prompt(
    messages: list[dict[str, Any]],
    *,
    response_format: object | None = None,
) -> str:
    system_parts: list[str] = []
    turns: list[str] = []
    for item in messages:
        role = str(item.get("role") or "").strip().lower()
        content = _message_text(item.get("content"))
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role == "assistant":
            turns.append(f"assistant: {content}")
        else:
            turns.append(f"user: {content}")

    json_mode = is_json_object_format(response_format)
    blocks = [_CHAT_PREAMBLE.strip()]
    if json_mode:
        blocks.append(_JSON_OBJECT_CONSTRAINT.strip())
    if system_parts:
        blocks.append("SYSTEM:\n" + "\n\n".join(system_parts))
    if turns:
        blocks.append("CONVERSATION:\n" + "\n".join(turns))
    if json_mode:
        blocks.append("Respond to the latest user message now with a single JSON object only.")
    else:
        blocks.append("Respond to the latest user message now.")
    return "\n\n".join(blocks)


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""
