from __future__ import annotations

import time
import uuid
from typing import Any


def openai_models_payload(model_ids: list[str]) -> dict[str, Any]:
    created = int(time.time())
    data = [
        {
            "id": model_id,
            "object": "model",
            "created": created,
            "owned_by": "cursor",
        }
        for model_id in model_ids
    ]
    return {"object": "list", "data": data}


def openai_completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


def openai_non_stream_response(*, model: str, content: str, completion_id: str) -> dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
