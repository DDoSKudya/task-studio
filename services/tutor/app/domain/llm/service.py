from __future__ import annotations

from app.domain.llm.client import (
    complete_chat_completion,
    complete_chat_result,
    stream_chat_completion,
)
from app.domain.llm.continue_text import complete_json_raw_until_done, complete_text_until_done
from app.domain.llm.json_mode import (
    complete_json_chat_completion,
    complete_json_chat_result,
    looks_like_unsupported_json_mode,
)
from app.domain.llm.result import ChatCompletionResult
from app.domain.llm.target import (
    LlmTarget,
    decrypt_tutor_api_key,
    is_cursor_target,
    is_ollama_target,
    resolve_llm_target,
    with_task,
)

__all__ = [
    "ChatCompletionResult",
    "LlmTarget",
    "complete_chat_completion",
    "complete_chat_result",
    "complete_json_chat_completion",
    "complete_json_chat_result",
    "complete_json_raw_until_done",
    "complete_text_until_done",
    "decrypt_tutor_api_key",
    "is_cursor_target",
    "is_ollama_target",
    "looks_like_unsupported_json_mode",
    "resolve_llm_target",
    "with_task",
    "stream_chat_completion",
]
