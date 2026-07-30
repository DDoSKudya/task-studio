from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .constants import _MAX_CHAPTERS
from .messages import _analyze_chapter_user_message, _analyze_user_message
from .normalize import (
    _normalize_book_spine,
    _normalize_chapters,
    _normalize_domain,
)
from .pipeline_hooks import _stage_json
from .progress import _band_progress, _stage_event
from .textutil import _as_str, _slug, _string_list


@dataclass
class AnalyzeStageResult:
    chapters: list[dict[str, str]] = field(default_factory=list)
    book_spine: dict[str, str] = field(default_factory=dict)
    outcomes: list[str] = field(default_factory=list)
    domain: str = "general"
    pack_id: str = "article-course"
    title: str = "Article Course"
    locale: str = "en"
    warning: str | None = None


def _chapter_detail_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    chapter = payload.get("chapter")
    if isinstance(chapter, dict):
        return chapter

    if "chapters" in payload or "pack_id" in payload or "book_spine" in payload:
        return None
    if payload.get("source_excerpt") or payload.get("purpose") or payload.get("bridge_from_prev"):
        return payload
    return None


async def _enrich_one_chapter(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    article: str,
    sources: list[dict[str, object]],
    chapter: dict[str, str],
    index: int,
    total: int,
    outcomes: list[str],
) -> dict[str, str]:
    try:
        payload = await _stage_json(
            client,
            target,
            compact=compact,
            stage="analyze",
            user_message=_analyze_chapter_user_message(
                body,
                article,
                sources=sources,
                chapter=chapter,
                index=index,
                total=total,
                outcomes=outcomes,
            ),
            max_tokens=900 if compact else 1600,
        )
    except TutorError:
        return chapter
    detail = _chapter_detail_payload(payload)
    if detail is None:
        return chapter
    merged = _normalize_chapters([{**chapter, **detail}])
    return merged[0] if merged else chapter


async def iter_analyze_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    article: str,
    sources: list[dict[str, object]],
    band_analyze: tuple[float, float],
    result: AnalyzeStageResult,
) -> AsyncIterator[dict[str, object]]:
    yield _stage_event(
        stage="analyze",
        status="running",
        progress=band_analyze[0],
        message="Synthesizing one progressive syllabus from all sources",
        message_key="analyzeRunning",
        detail={"locale": body.locale, "audience": body.audience, "article_count": len(sources)},
    )

    analysis = await _stage_json(
        client,
        target,
        compact=compact,
        stage="analyze",
        user_message=_analyze_user_message(body, article, sources=sources),
        max_tokens=2200 if compact else 3600,
    )
    chapters = _normalize_chapters(analysis.get("chapters"))
    if not chapters:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course analyze returned no chapters")
    if len(chapters) > _MAX_CHAPTERS:
        result.warning = f"trimmed chapters to {_MAX_CHAPTERS}"
        chapters = chapters[:_MAX_CHAPTERS]

    book_spine = _normalize_book_spine(analysis.get("book_spine"))
    outcomes = _string_list(analysis.get("outcomes"))
    domain = _normalize_domain(
        analysis.get("domain"),
        article=article,
        title=_as_str(analysis.get("title")) or _as_str(body.title) or "",
    )
    pack_id = _slug(
        _as_str(analysis.get("pack_id"))
        or _as_str(body.title)
        or _as_str(analysis.get("title"))
        or "article-course"
    )
    title = (
        _as_str(body.title) or _as_str(analysis.get("title")) or pack_id.replace("-", " ").title()
    )
    locale = _as_str(analysis.get("locale")) or body.locale

    units = 1 + len(chapters)
    skeleton = [{"id": c["id"], "title": c["title"]} for c in chapters]
    yield _stage_event(
        stage="analyze",
        status="running",
        progress=_band_progress(band_analyze, 1, units),
        message="Syllabus outline ready — enriching chapters",
        message_key="analyzeOutlineReady",
        detail={
            "title": title,
            "pack_id": pack_id,
            "domain": domain,
            "outcomes": outcomes,
            "chapters": skeleton,
            "chapter_count": len(chapters),
            "phase": "enrich",
        },
    )

    enriched: list[dict[str, str]] = []
    total = len(chapters)
    for index, chapter in enumerate(chapters):
        yield _stage_event(
            stage="analyze",
            status="running",
            progress=_band_progress(band_analyze, 1 + index, units),
            message=f"Enriching chapter: {chapter['title']}",
            message_key="analyzeEnriching",
            message_params={"title": chapter["title"], "index": index + 1, "total": total},
            index=index + 1,
            total=total,
            detail={
                "chapter_id": chapter["id"],
                "chapter_title": chapter["title"],
                "chapters": skeleton,
                "phase": "enrich",
                "mode": "serial",
            },
        )
        enriched_chapter = await _enrich_one_chapter(
            client,
            target,
            body=body,
            compact=compact,
            article=article,
            sources=sources,
            chapter=chapter,
            index=index,
            total=total,
            outcomes=outcomes,
        )
        enriched.append(enriched_chapter)
        skeleton[index] = {
            "id": enriched_chapter["id"],
            "title": enriched_chapter["title"],
        }

    result.chapters = enriched
    result.book_spine = book_spine
    result.outcomes = outcomes
    result.domain = domain
    result.pack_id = pack_id
    result.title = title
    result.locale = locale

    yield _stage_event(
        stage="analyze",
        status="done",
        progress=band_analyze[1],
        message="Outline ready",
        message_key="analyzeDone",
        detail={
            "title": title,
            "pack_id": pack_id,
            "domain": domain,
            "outcomes": outcomes,
            "chapters": [{"id": c["id"], "title": c["title"]} for c in enriched],
            "chapter_count": len(enriched),
            "has_book_spine": bool(book_spine.get("throughline") or book_spine.get("voice")),
        },
    )
