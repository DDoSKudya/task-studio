from __future__ import annotations

import httpx
from app.domain.ollama.defaults import OLLAMA_NUM_CTX as _OLLAMA_NUM_CTX
from app.domain.ollama.quality import (
    ReplyLanguage,
    polish_system_prompt,
    polish_user_message,
)

from .models import (
    _OLLAMA_POLISH_MAX_TOKENS,
    _OLLAMA_POLISH_TEMPERATURE,
    _OLLAMA_POLISH_TOP_P,
    ChatContext,
    _complete_chat_completion,
)


async def polish_ollama_reply(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    draft: str,
    learner_message: str,
    language: ReplyLanguage,
) -> str:
    return await _complete_chat_completion(
        client,
        context.target,
        system_prompt=polish_system_prompt(language),
        user_message=polish_user_message(
            draft,
            language=language,
            learner_message=learner_message,
        ),
        conversation_id=context.conversation_id,
        temperature=_OLLAMA_POLISH_TEMPERATURE,
        top_p=_OLLAMA_POLISH_TOP_P,
        max_tokens=_OLLAMA_POLISH_MAX_TOKENS,
        num_ctx=_OLLAMA_NUM_CTX,
    )
