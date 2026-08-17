from __future__ import annotations

import httpx
from app.domain.chat.session.models import (
    OLLAMA_POLISH_MAX_TOKENS,
    OLLAMA_POLISH_TEMPERATURE,
    OLLAMA_POLISH_TOP_P,
    ChatContext,
    complete_bound_chat,
)
from app.domain.ollama.defaults import OLLAMA_NUM_CTX
from app.domain.ollama.quality import (
    ReplyLanguage,
    polish_system_prompt,
    polish_user_message,
)


async def polish_ollama_reply(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    draft: str,
    learner_message: str,
    language: ReplyLanguage,
) -> str:
    return await complete_bound_chat(
        client,
        context.target,
        system_prompt=polish_system_prompt(language),
        user_message=polish_user_message(
            draft,
            language=language,
            learner_message=learner_message,
        ),
        conversation_id=context.conversation_id,
        temperature=OLLAMA_POLISH_TEMPERATURE,
        top_p=OLLAMA_POLISH_TOP_P,
        max_tokens=OLLAMA_POLISH_MAX_TOKENS,
        num_ctx=OLLAMA_NUM_CTX,
    )
