from __future__ import annotations

from app.domain.ollama.quality_lang import LANGUAGE_NAMES, ReplyLanguage

_COURSE_LOCALES = frozenset({"ru", "en"})


def normalize_course_locale(raw: object) -> ReplyLanguage:
    value = str(raw or "").strip().casefold()
    if value.startswith("ru"):
        return "ru"
    if value.startswith("en"):
        return "en"
    return "ru"


def course_language_name(locale: object) -> str:
    return LANGUAGE_NAMES[normalize_course_locale(locale)]


def locale_prompt_block(locale: object) -> str:
    """Hard rule: learner-facing course text follows the form locale, not the source."""
    code = normalize_course_locale(locale)
    name = LANGUAGE_NAMES[code]
    return "\n".join(
        [
            f"## Locale\n{code}",
            "## Output language (mandatory)",
            f"Write ALL learner-facing text in {name} ({code}) only: "
            "course title, chapter titles, theory prose, quiz questions/choices, "
            "task briefs, rubrics, outcomes, book_spine voice/address/throughline/glossary.",
            "Source articles may be in ANY language (Arabic, Chinese, English, …). "
            "Read them for facts; translate and teach in the locale above. "
            "Do NOT keep the source language for titles or explanations.",
            "Code identifiers, SQL keywords, and API names stay as in the materials "
            "(usually English) inside fenced code — surrounding prose stays in the locale.",
            f'JSON field "locale" must be exactly "{code}".',
        ]
    )
