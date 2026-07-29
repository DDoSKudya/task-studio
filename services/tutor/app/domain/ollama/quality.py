from __future__ import annotations

from app.domain.ollama.quality_lang import (
    LANGUAGE_NAMES,
    ReplyLanguage,
    has_unexpected_scripts,
    infer_reply_language,
    language_mismatch,
    needs_quality_retry,
    prose_without_code,
)
from app.domain.prompt_compose import load_prompt, render_prompt

__all__ = [
    "ReplyLanguage",
    "infer_reply_language",
    "prose_without_code",
    "has_unexpected_scripts",
    "language_mismatch",
    "needs_quality_retry",
    "pick_better_reply",
    "polish_system_prompt",
    "polish_user_message",
]


def pick_better_reply(draft: str, polished: str, *, language: ReplyLanguage) -> str:
    cleaned = polished.strip()
    if not cleaned:
        return draft
    draft_bad = needs_quality_retry(draft, language)
    polish_bad = needs_quality_retry(cleaned, language)
    if polish_bad and not draft_bad:
        return draft
    return cleaned


def polish_system_prompt(language: ReplyLanguage) -> str:
    template = load_prompt("provider/ollama-polish")
    return render_prompt(template, language_name=LANGUAGE_NAMES[language])


def polish_user_message(
    draft: str,
    *,
    language: ReplyLanguage,
    learner_message: str,
) -> str:
    language_name = LANGUAGE_NAMES[language]
    return (
        f"Learner message language: {language_name}\n"
        f"Learner message:\n{learner_message.strip()}\n\n"
        f"Draft tutor reply to clean:\n{draft.strip()}\n\n"
        f"Rewrite the draft in {language_name} only."
    )
