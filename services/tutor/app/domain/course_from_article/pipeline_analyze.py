from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .constants import _MAX_CHAPTERS, _MAX_CHAPTERS_COMPACT
from .course_locale import normalize_course_locale
from .messages import (
    _analyze_chapter_user_message,
    _analyze_user_message,
    _expand_outline_user_message,
)
from .normalize import (
    _normalize_book_spine,
    _normalize_chapters,
    _normalize_domain,
)
from .pipeline_hooks import _stage_json
from .progress import _band_progress, _stage_event
from .source_images import attach_source_images_to_chapters
from .textutil import _as_str, _slug, _string_list


@dataclass
class AnalyzeStageResult:
    chapters: list[dict[str, str]] = field(default_factory=list)
    book_spine: dict[str, str] = field(default_factory=dict)
    outcomes: list[str] = field(default_factory=list)
    domain: str = "general"
    course_profile: str = ""
    pack_id: str = "article-course"
    title: str = "Article Course"
    locale: str = "en"
    warning: str | None = None


def _analyze_outline_max_tokens(*, compact: bool, chapter_cap: int) -> int:
    per_chapter = 55 if compact else 90
    base = 900 if compact else 2400
    ceiling = 2800 if compact else 12_000
    return min(ceiling, base + max(1, chapter_cap) * per_chapter)


async def _expand_chapters_toward_target(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    article: str,
    chapters: list[dict[str, str]],
    chapter_cap: int,
) -> list[dict[str, str]]:
    if len(chapters) >= chapter_cap:
        return chapters
    # Не раздуваем outline, если на слайд останется меньше ~2.5k символов корпуса.
    if len(article) < chapter_cap * 2_500:
        return chapters
    # Добиваем только заметный недобор (иначе оставляем честный analyze).
    if len(chapters) >= max(2, int(chapter_cap * 0.7)):
        return chapters
    payload = await _stage_json(
        client,
        target,
        compact=compact,
        stage="analyze",
        user_message=_expand_outline_user_message(
            body,
            article,
            chapters=chapters,
            target=chapter_cap,
        ),
        max_tokens=_analyze_outline_max_tokens(compact=compact, chapter_cap=chapter_cap),
    )
    expanded = _normalize_chapters(payload.get("chapters"))
    if len(expanded) <= len(chapters):
        return chapters
    return expanded[:chapter_cap] if len(expanded) > chapter_cap else expanded


def _chapter_detail_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    chapter = payload.get("chapter")
    if isinstance(chapter, dict):
        return chapter

    if "chapters" in payload or "pack_id" in payload or "book_spine" in payload:
        return None
    detail_keys = (
        "source_excerpt",
        "purpose",
        "learning_objective",
        "bridge_from_prev",
    )
    if any(payload.get(key) for key in detail_keys):
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

    wanted = body.effective_theory_count()
    hard_max = _MAX_CHAPTERS_COMPACT if compact else _MAX_CHAPTERS
    chapter_cap = min(max(1, int(wanted or hard_max)), hard_max)

    analysis = await _stage_json(
        client,
        target,
        compact=compact,
        stage="analyze",
        user_message=_analyze_user_message(body, article, sources=sources, compact=compact),
        max_tokens=_analyze_outline_max_tokens(compact=compact, chapter_cap=chapter_cap),
    )
    chapters = _normalize_chapters(analysis.get("chapters"))
    if not chapters:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course analyze returned no chapters")
    if len(chapters) > chapter_cap:
        result.warning = f"trimmed chapters to {chapter_cap}"
        chapters = chapters[:chapter_cap]
    elif wanted is not None and len(chapters) < chapter_cap:
        chapters = await _expand_chapters_toward_target(
            client,
            target,
            body=body,
            compact=compact,
            article=article,
            chapters=chapters,
            chapter_cap=chapter_cap,
        )
        if len(chapters) < chapter_cap:
            result.warning = (
                f"sources supported {len(chapters)} of {chapter_cap} requested theory slides"
            )
        else:
            result.warning = f"expanded outline to {chapter_cap} theory slides"

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
    locale = normalize_course_locale(body.locale)
    title = (
        _as_str(body.title) or _as_str(analysis.get("title")) or pack_id.replace("-", " ").title()
    )

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

    enriched = []
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

    result.chapters = attach_source_images_to_chapters(enriched, sources)
    result.book_spine = book_spine
    result.outcomes = outcomes
    result.domain = domain
    result.course_profile = (
        _as_str(analysis.get("course_profile")) or _as_str(analysis.get("domain_profile")) or ""
    )
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
