from __future__ import annotations

from app.domain.ollama.quality_lang import LANGUAGE_NAMES, ReplyLanguage

_COURSE_LOCALES = frozenset({"ru", "en"})
_MIN_CATALOG_LETTERS = 8


def normalize_course_locale(raw: object) -> ReplyLanguage:
    value = str(raw or "").strip().casefold()
    if value.startswith("ru"):
        return "ru"
    if value.startswith("en"):
        return "en"
    return "ru"


def course_language_name(locale: object) -> str:
    return LANGUAGE_NAMES[normalize_course_locale(locale)]


def locale_line(locale: object) -> str:
    code = normalize_course_locale(locale)
    name = LANGUAGE_NAMES[code]
    address = "ты" if code == "ru" else "you"
    return (
        f"Course locale: {code} ({name}). "
        f"Write ALL learner-facing text in {name} only. "
        f"Address the learner as {address}. "
        "The source article may be in ANY language — that does not matter. "
        "Read it for facts only; translate and teach in the course locale. "
        "Do not keep source-language titles or explanations. "
        "Code identifiers stay as in the excerpt."
    )


def catalog_text_mismatches_locale(text: object, locale: object) -> bool:
    code = normalize_course_locale(locale)
    letters = [ch for ch in str(text or "") if ch.isalpha()]
    if len(letters) < _MIN_CATALOG_LETTERS:
        return False
    cyrillic = sum("\u0400" <= ch <= "\u04ff" for ch in letters)
    ratio = cyrillic / len(letters)
    return ratio < 0.25 if code == "ru" else ratio > 0.55


def catalog_needs_locale_rewrite(
    chapters: list[dict[str, str]],
    outcomes: list[str] | None = None,
    locale: object = "ru",
) -> bool:
    parts: list[str] = []
    for item in chapters:
        parts.extend((str(item.get("title") or ""), str(item.get("objective") or "")))
    parts.extend(str(item) for item in (outcomes or []))
    return any(catalog_text_mismatches_locale(part, locale) for part in parts if part.strip())


def locale_prompt_block(locale: object) -> str:

    code = normalize_course_locale(locale)
    name = LANGUAGE_NAMES[code]
    return "\n".join(
        [
            f"## Locale\n{code}",
            "## Output language (mandatory)",
            f"Write ALL learner-facing text in {name} ({code}) only: "
            "course title, chapter titles, theory prose, quiz questions/choices, "
            "task briefs, rubrics, outcomes, book_spine voice/address/throughline/glossary.",
            "The source article may be in ANY language (Arabic, Chinese, English, …). "
            "That does not matter. Read it for facts; translate and teach in the locale above. "
            "Do NOT keep the source language for titles or explanations.",
            "Code identifiers, SQL keywords, and API names stay as in the materials "
            "(usually English) inside fenced code — surrounding prose stays in the locale.",
            f'JSON field "locale" must be exactly "{code}".',
        ]
    )
