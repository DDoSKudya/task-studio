from __future__ import annotations

from app.domain.course_from_article.curriculum.outline.course_locale import normalize_course_locale


def build_local_book_spine(
    *,
    locale: str,
    title: str,
    chapters: list[dict[str, str]],
    outcomes: list[str],
) -> dict[str, str]:

    ru = normalize_course_locale(locale) == "ru"
    titles = [
        str(item.get("title") or "").strip()
        for item in chapters
        if str(item.get("title") or "").strip()
    ]
    arc = " → ".join(titles[:12])
    goals = "; ".join(str(item).strip() for item in outcomes[:4] if str(item).strip())

    throughline = goals if goals else (arc or title)
    return {
        "voice": (
            "уверенный учебник: одна идея на главу, мост в следующую, без повторных вступлений"
            if ru
            else "confident textbook: one idea per chapter, bridge to the next, no repeated intros"
        ),
        "address": "ты" if ru else "you",
        "throughline": throughline[:600],
        "glossary": "",
        "metaphors": "",
    }


def merge_book_spine(
    spine: dict[str, str] | None,
    *,
    locale: str,
    title: str,
    chapters: list[dict[str, str]],
    outcomes: list[str],
) -> dict[str, str]:
    built = build_local_book_spine(locale=locale, title=title, chapters=chapters, outcomes=outcomes)
    if not spine:
        return built
    throughline = str(spine.get("throughline") or "").strip()
    first_title = chapters[0]["title"] if chapters else ""
    if not throughline or throughline == first_title:
        throughline = built["throughline"]
    return {
        "voice": str(spine.get("voice") or "").strip() or built["voice"],
        "address": str(spine.get("address") or "").strip() or built["address"],
        "throughline": throughline[:600],
        "glossary": str(spine.get("glossary") or ""),
        "metaphors": str(spine.get("metaphors") or spine.get("recurring_metaphors") or ""),
    }
