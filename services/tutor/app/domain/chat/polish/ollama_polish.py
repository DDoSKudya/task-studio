from __future__ import annotations

import httpx
from app.domain.chat.polish.ollama_polish_pass import polish_ollama_reply
from app.domain.chat.session.models import (
    OLLAMA_DRAFT_MAX_TOKENS,
    OLLAMA_DRAFT_TEMPERATURE,
    OLLAMA_DRAFT_TOP_P,
    ChatContext,
    complete_bound_chat,
)
from app.domain.ollama.defaults import OLLAMA_NUM_CTX
from app.domain.ollama.quality import (
    infer_reply_language,
    needs_quality_retry,
    pick_better_reply,
)
from app.domain.prompt_compose import format_learner_turn

__all__ = ["ollama_draft_and_polish", "polish_ollama_reply"]


async def ollama_draft_and_polish(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    message: str,
    history: list[dict[str, str]] | None,
) -> str:
    language = infer_reply_language(message)
    draft = await complete_bound_chat(
        client,
        context.target,
        system_prompt=context.system_prompt,
        user_message=format_learner_turn(message),
        history=history,
        conversation_id=context.conversation_id,
        temperature=OLLAMA_DRAFT_TEMPERATURE,
        top_p=OLLAMA_DRAFT_TOP_P,
        max_tokens=OLLAMA_DRAFT_MAX_TOKENS,
        num_ctx=OLLAMA_NUM_CTX,
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
