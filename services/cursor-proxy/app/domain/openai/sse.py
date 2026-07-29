from __future__ import annotations

import json

_CHUNK_SIZE = 48


def chunk_text(content: str, size: int = _CHUNK_SIZE) -> list[str]:
    text = content.strip()
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def openai_role_chunk(*, model: str, completion_id: str, created: int) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def openai_content_chunk(*, model: str, completion_id: str, created: int, text: str) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": text},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def openai_stop_chunk(*, model: str, completion_id: str, created: int) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def openai_error_chunk(message: str, *, code: int) -> str:
    payload = {
        "error": {
            "message": message,
            "type": "cursor_proxy_error",
            "code": code,
        }
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
