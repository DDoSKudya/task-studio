from __future__ import annotations

import re
from typing import Any

from app.domain.course_from_article.common.content.constants import _MAX_SOURCE_EXCERPT
from app.domain.course_from_article.common.content.textutil import _as_str, _join_string_list, _slug
from app.domain.course_from_article.pack.assemble import _retarget_code_fences
from app.domain.course_from_article.pack.source_images import filter_theory_images
from app.domain.course_from_article.practice.source_exercise_harvest import (
    strip_theory_exercise_sections,
)
from app.domain.llm.content.prose_dedupe import collapse_repeated_prose, strip_throat_clearing
from studio_contracts.api.studio_schemas import CourseDeviation


def _normalize_deviations(raw: object, sources: list[dict[str, object]]) -> list[CourseDeviation]:
    if not isinstance(raw, list):
        return []
    titles = [str(item["title"]) for item in sources]
    out: list[CourseDeviation] = []
    for item in raw[:5]:
        if not isinstance(item, dict):
            continue
        summary = _as_str(item.get("summary"))
        if not summary:
            continue
        source_names = item.get("sources")
        names: list[str] = []
        if isinstance(source_names, list):
            names = [str(name).strip() for name in source_names if str(name).strip()][:4]
        if not names:
            names = titles[:2]
        out.append(CourseDeviation(summary=summary, sources=names))
    return out


def _title_fingerprint(title: str) -> frozenset[str]:
    stop = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "vs",
        "via",
        "from",
        "into",
        "about",
        "your",
        "you",
        "we",
        "our",
        "is",
        "are",
        "be",
        "how",
        "what",
        "why",
        "when",
        "guide",
        "intro",
        "introduction",
        "и",
        "в",
        "на",
        "по",
        "для",
        "с",
        "к",
        "о",
        "не",
        "ни",
        "же",
        "ли",
        "бы",
        "как",
        "без",
        "всё",
        "все",
        "этот",
        "эта",
        "это",
        "чтобы",
        "или",
        "из",
        "от",
        "до",
        "при",
        "хватит",
        "писать",
        "пишем",
        "гайд",
        "часть",
        "урок",
        "глава",
        "py",
        "js",
        "ts",
        "md",
    }
    tokens = re.findall(r"[a-z0-9а-яё]+", title.casefold())
    return frozenset(token for token in tokens if token not in stop and len(token) > 2)


def _titles_near_duplicate(left: str, right: str) -> bool:
    if left.casefold() == right.casefold():
        return True
    left_fp = _title_fingerprint(left)
    right_fp = _title_fingerprint(right)
    if len(left_fp) < 2 or len(right_fp) < 2:
        return False
    overlap = left_fp & right_fp
    if len(overlap) < 3 and min(len(left_fp), len(right_fp)) >= 4:
        return False
    union = left_fp | right_fp
    jaccard = len(overlap) / max(1, len(union))
    return jaccard >= 0.66 and len(overlap) >= 2


def _unique_chapter_title(title: str, *, seen: dict[str, int], prior: list[str]) -> str:
    for existing in prior:
        if _titles_near_duplicate(title, existing):
            key = existing.casefold()
            count = seen.get(key, 1) + 1
            seen[key] = count
            return f"{existing} ({count})"
    key = title.casefold()
    count = seen.get(key, 0) + 1
    seen[key] = count
    return title if count == 1 else f"{title} ({count})"


def _unique_chapter_id(chapter_id: str, *, seen: set[str]) -> str:
    if chapter_id not in seen:
        seen.add(chapter_id)
        return chapter_id
    suffix = 2
    while f"{chapter_id}-{suffix}" in seen:
        suffix += 1
    unique = f"{chapter_id}-{suffix}"
    seen.add(unique)
    return unique


def _excerpt_fingerprint(excerpt: str) -> frozenset[str]:
    return _title_fingerprint(excerpt[:2500])


def _excerpts_near_duplicate(left: str, right: str) -> bool:
    left_fp = _excerpt_fingerprint(left)
    right_fp = _excerpt_fingerprint(right)
    if len(left_fp) < 4 or len(right_fp) < 4:
        return False
    overlap = left_fp & right_fp
    union = left_fp | right_fp
    return len(overlap) / max(1, len(union)) >= 0.55 and len(overlap) >= 4


_JUDGEABLE_EXCERPT_CHARS = 200


def topics_are_duplicates(
    *,
    left_title: str,
    left_excerpt: str,
    right_title: str,
    right_excerpt: str,
) -> bool:
    """Дубликат — когда совпали и заголовок, и содержание.

    Один заголовок на два разных куска материала — обычное дело для длинного корпуса:
    окна без своего подзаголовка наследуют имя источника. Схлопывать их по имени значит
    терять текст. Слишком короткие отрывки сравнивать нечем — там решает заголовок.
    """

    if not _titles_near_duplicate(left_title, right_title):
        return False
    if min(len(left_excerpt), len(right_excerpt)) < _JUDGEABLE_EXCERPT_CHARS:
        return True
    return _excerpts_near_duplicate(left_excerpt, right_excerpt)


def _normalize_chapters(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    chapters: list[dict[str, str]] = []
    seen_titles: dict[str, int] = {}
    prior_titles: list[str] = []
    prior_excerpts: list[str] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        raw_title = _as_str(item.get("title")) or f"Chapter {index + 1}"
        excerpt = _as_str(item.get("source_excerpt")) or _as_str(item.get("excerpt")) or raw_title
        drop = any(
            _titles_near_duplicate(raw_title, existing_title)
            and _excerpts_near_duplicate(excerpt, existing_excerpt)
            for existing_title, existing_excerpt in zip(prior_titles, prior_excerpts, strict=True)
        )
        if drop:
            continue
        title = _unique_chapter_title(
            raw_title,
            seen=seen_titles,
            prior=prior_titles,
        )
        chapter_id = _unique_chapter_id(
            _slug(_as_str(item.get("id")) or title),
            seen=seen_ids,
        )
        purpose = _as_str(item.get("purpose")) or ""
        learning_objective = _as_str(item.get("learning_objective")) or ""
        source_titles_raw = item.get("source_titles")
        source_titles = ""
        if isinstance(source_titles_raw, list):
            names = [str(name).strip() for name in source_titles_raw if str(name).strip()]
            source_titles = ", ".join(names[:6])
        elif isinstance(source_titles_raw, str):
            source_titles = source_titles_raw.strip()
        prior_titles.append(raw_title)
        prior_excerpts.append(excerpt[:_MAX_SOURCE_EXCERPT])
        chapters.append(
            {
                "id": chapter_id,
                "title": title,
                "source_excerpt": excerpt[:_MAX_SOURCE_EXCERPT],
                "purpose": purpose[:320],
                "learning_objective": learning_objective[:320],
                "source_titles": source_titles[:400],
                "bridge_from_prev": (_as_str(item.get("bridge_from_prev")) or "")[:320],
                "assumes_known": _join_string_list(item.get("assumes_known"), limit=8)[:400],
                "must_not_reteach": _join_string_list(item.get("must_not_reteach"), limit=8)[:400],
                "source_images": (_as_str(item.get("source_images")) or "")[:2_000],
            }
        )
    return chapters


def _normalize_book_spine(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {
            "voice": "",
            "address": "",
            "throughline": "",
            "glossary": "",
            "metaphors": "",
        }
    glossary_raw = raw.get("glossary")
    glossary_bits: list[str] = []
    if isinstance(glossary_raw, list):
        for item in glossary_raw[:12]:
            if isinstance(item, dict):
                term = _as_str(item.get("term")) or ""
                sense = _as_str(item.get("sense")) or _as_str(item.get("definition")) or ""
                if term:
                    if sense:
                        glossary_bits.append(f"{term}: {sense}")
                    else:
                        glossary_bits.append(term)
            elif text := str(item).strip():
                glossary_bits.append(text)
    elif isinstance(glossary_raw, str) and glossary_raw.strip():
        glossary_bits.append(glossary_raw.strip())
    metaphors = _join_string_list(raw.get("recurring_metaphors") or raw.get("metaphors"), limit=6)
    return {
        "voice": (_as_str(raw.get("voice")) or "")[:240],
        "address": (_as_str(raw.get("address")) or "")[:40],
        "throughline": (_as_str(raw.get("throughline")) or "")[:400],
        "glossary": "; ".join(glossary_bits)[:800],
        "metaphors": metaphors[:400],
    }


def _normalize_theory_step(raw: dict[str, Any], chapter: dict[str, str]) -> dict[str, object]:
    step_id = _slug(_as_str(raw.get("id")) or f"theory-{chapter['id']}")
    if not step_id.startswith("theory"):
        step_id = f"theory-{step_id}"
    content = (_as_str(raw.get("content")) or "").strip()
    if content:
        content = _retarget_code_fences(content)
        content = strip_theory_exercise_sections(content)
        content = strip_throat_clearing(collapse_repeated_prose(content))
    allowed = {
        match.group(1)
        for match in re.finditer(r"\((https?://[^)\s]+)\)", chapter.get("source_images") or "")
    }
    content, image_urls = filter_theory_images(content, allowed_urls=allowed)
    title = _as_str(raw.get("title")) or chapter["title"]
    step: dict[str, object] = {
        "id": step_id,
        "kind": "theory",
        "title": title,
        "content": content,
        "chapter_id": chapter["id"],
    }
    if image_urls:
        step["images"] = image_urls
    claims = raw.get("key_claims")
    if isinstance(claims, list) and claims:
        step["key_claims"] = [str(item) for item in claims if str(item).strip()][:6]
    visual = raw.get("visual_plan")
    if isinstance(visual, dict) and visual:
        step["visual_plan"] = {
            str(key): str(value) for key, value in visual.items() if str(value).strip()
        }
    return step


def _normalize_domain(raw: object, *, article: str, title: str) -> str:
    value = (_as_str(raw) or "").casefold().replace("-", "_")
    if value in {"code", "language", "general"}:
        return value

    fine_to_coarse = {
        "programming": "code",
        "data": "code",
        "language_learning": "language",
        "humanities": "general",
        "business": "general",
        "science_general": "general",
        "science": "general",
    }
    if mapped := fine_to_coarse.get(value):
        return mapped
    blob = f"{title}\n{article[:4000]}".casefold()
    lang_tokens = (
        "english",
        "grammar",
        "vocabulary",
        "перевод",
        "английск",
        "ielts",
        "toefl",
    )
    if any(token in blob for token in lang_tokens):
        return "language"
    code_tokens = (
        "def ",
        "class ",
        "select ",
        "function ",
        "```",
        "api",
        "sql",
        "python",
        "javascript",
        "command line",
        "shell",
        "configuration",
        "deployment",
        "infrastructure",
    )
    if any(token in blob for token in code_tokens):
        return "code"
    return "general"
