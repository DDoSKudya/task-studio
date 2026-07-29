from __future__ import annotations

import httpx
from app.domain.ollama.defaults import OLLAMA_NUM_CTX as _OLLAMA_NUM_CTX
from app.domain.ollama.quality import (
    infer_reply_language,
    needs_quality_retry,
    pick_better_reply,
)
from app.domain.prompt_compose import format_learner_turn

from .models import (
    _OLLAMA_DRAFT_MAX_TOKENS,
    _OLLAMA_DRAFT_TEMPERATURE,
    _OLLAMA_DRAFT_TOP_P,
    ChatContext,
    _complete_chat_completion,
)
from .ollama_polish_pass import polish_ollama_reply

__all__ = ["ollama_draft_and_polish", "polish_ollama_reply"]


async def ollama_draft_and_polish(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    message: str,
    history: list[dict[str, str]] | None,
) -> str:
    language = infer_reply_language(message)
    draft = await _complete_chat_completion(
        client,
        context.target,
        system_prompt=context.system_prompt,
        user_message=format_learner_turn(message),
        history=history,
        conversation_id=context.conversation_id,
        temperature=_OLLAMA_DRAFT_TEMPERATURE,
        top_p=_OLLAMA_DRAFT_TOP_P,
        max_tokens=_OLLAMA_DRAFT_MAX_TOKENS,
        num_ctx=_OLLAMA_NUM_CTX,
    )
    polished = await polish_ollama_reply(
        client,
        context,
        draft=draft,
        learner_message=message,
        language=language,
    )
    best = pick_better_reply(draft, polished, language=language)
    if needs_quality_retry(best, language):
        again = await polish_ollama_reply(
            client,
            context,
            draft=best,
            learner_message=message,
            language=language,
        )
        best = pick_better_reply(best, again, language=language)
    return best
