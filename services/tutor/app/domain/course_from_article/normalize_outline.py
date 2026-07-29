from __future__ import annotations

from typing import Any

from studio_contracts.studio_schemas import CourseDeviation

from .assemble import _retarget_code_fences
from .textutil import _as_str, _join_string_list, _slug


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


def _normalize_chapters(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    chapters: list[dict[str, str]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        title = _as_str(item.get("title")) or f"Chapter {index + 1}"
        chapter_id = _slug(_as_str(item.get("id")) or title)
        excerpt = _as_str(item.get("source_excerpt")) or _as_str(item.get("excerpt")) or title
        purpose = _as_str(item.get("purpose")) or ""
        source_titles_raw = item.get("source_titles")
        source_titles = ""
        if isinstance(source_titles_raw, list):
            names = [str(name).strip() for name in source_titles_raw if str(name).strip()]
            source_titles = ", ".join(names[:6])
        elif isinstance(source_titles_raw, str):
            source_titles = source_titles_raw.strip()
        chapters.append(
            {
                "id": chapter_id,
                "title": title,
                "source_excerpt": excerpt[:1200],
                "purpose": purpose[:240],
                "source_titles": source_titles[:400],
                "bridge_from_prev": (_as_str(item.get("bridge_from_prev")) or "")[:240],
                "assumes_known": _join_string_list(item.get("assumes_known"), limit=8)[:400],
                "must_not_reteach": _join_string_list(item.get("must_not_reteach"), limit=8)[:400],
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
    content = _retarget_code_fences(_as_str(raw.get("content")) or chapter["source_excerpt"])
    title = _as_str(raw.get("title")) or chapter["title"]
    return {
        "id": step_id,
        "kind": "theory",
        "title": title,
        "content": content,
    }


def _normalize_domain(raw: object, *, article: str, title: str) -> str:
    value = (_as_str(raw) or "").casefold()
    if value in {"code", "language", "general"}:
        return value
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
        "docker",
    )
    if any(token in blob for token in code_tokens):
        return "code"
    return "general"
