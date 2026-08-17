from __future__ import annotations

import re

from app.domain.course_from_article.common.content.textutil import _slug
from app.domain.course_from_article.curriculum.outline.normalize_outline import (
    topics_are_duplicates,
)
from app.domain.course_strategies import sanitize_chapter_title

_NUM_PREFIX_RE = re.compile(r"^№?\s*\d+[.)]?\s+")
_WEAK_OBJECTIVE_MARKERS = (
    "understand",
    "know ",
    "learn about",
    "learn ",
    "понять",
    "узнать",
    "изучить",
    "ознакомиться",
    "введение",
    "introduction",
)


def polish_chapter_title(title: str) -> str:

    text = " ".join((title or "").split()).strip()
    text = _NUM_PREFIX_RE.sub("", text).strip()
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) >= 12:
        upper = sum(1 for ch in letters if ch.isupper())
        if upper / len(letters) >= 0.7:
            text = text[:1].upper() + text[1:].lower()
    return sanitize_chapter_title(text, fallback="Topic")


def ensure_measurable_objective(title: str, objective: str, *, locale: str = "ru") -> str:

    cleaned = " ".join((objective or "").split()).strip() or title.strip()
    folded = cleaned.casefold()
    weak = (
        len(cleaned) < 24
        or cleaned.casefold() == (title or "").casefold()
        or any(marker in folded for marker in _WEAK_OBJECTIVE_MARKERS)
    )
    if not weak:
        return cleaned[:400]
    skill = polish_chapter_title(title) or cleaned
    if (locale or "ru").casefold().startswith("ru"):
        return f"После главы уметь объяснить и применить: {skill}"[:400]
    return f"After this chapter, explain and apply: {skill}"[:400]


def syllabus_has_excerpts(chapters: list[dict[str, str]]) -> bool:
    if not chapters:
        return False
    fingerprints: list[str] = []
    for item in chapters:
        excerpt = (item.get("source_excerpt") or "").strip()
        title = (item.get("title") or "").strip()
        if not excerpt or excerpt.casefold() == title.casefold():
            return False
        fingerprints.append(excerpt[:500].casefold())
    return not (len(fingerprints) >= 2 and len(set(fingerprints)) == 1)


def _same_chapter(left: dict[str, str], right: dict[str, str]) -> bool:
    return topics_are_duplicates(
        left_title=str(left.get("title") or "").strip(),
        left_excerpt=str(left.get("source_excerpt") or ""),
        right_title=str(right.get("title") or "").strip(),
        right_excerpt=str(right.get("source_excerpt") or ""),
    )


def chapter_titles_are_unique(chapters: list[dict[str, str]]) -> bool:
    named = [item for item in chapters if str(item.get("title") or "").strip()]
    if len(named) < 2:
        return True
    return not any(
        _same_chapter(left, right)
        for index, left in enumerate(named)
        for right in named[index + 1 :]
    )


def normalize_local_chapters(
    raw: object,
    *,
    max_chapters: int,
    locale: str = "ru",
) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    chapters: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        title = polish_chapter_title(str(item.get("title") or "").strip())
        if not title:
            continue
        objective = ensure_measurable_objective(
            title,
            str(item.get("objective") or item.get("goal") or "").strip(),
            locale=locale,
        )
        excerpt = str(item.get("source_excerpt") or item.get("excerpt") or "").strip()
        chapter_id = _slug(str(item.get("id") or title))[:64] or f"ch-{index + 1}"
        if chapter_id in seen_ids:
            chapter_id = f"{chapter_id}-{index + 1}"
        seen_ids.add(chapter_id)
        chapters.append(
            {
                "id": chapter_id,
                "title": title[:70],
                "objective": objective[:400],
                "source_excerpt": excerpt[:9000],
            }
        )
        if len(chapters) >= max_chapters:
            break
    return chapters


def reject_duplicate_titles(chapters: list[dict[str, str]]) -> list[dict[str, str]]:

    kept: list[dict[str, str]] = []
    for chapter in chapters:
        if any(_same_chapter(chapter, prior) for prior in kept):
            continue
        kept.append(chapter)
    return kept
