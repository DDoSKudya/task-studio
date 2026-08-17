from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from app.domain.course_from_article.common.content.constants import (
    _MAX_CHAPTERS,
    _MAX_CHAPTERS_COMPACT,
)
from app.domain.course_from_article.common.content.messages import (
    _analyze_chapter_user_message,
    _analyze_user_message,
)
from app.domain.course_from_article.common.content.normalize import (
    _normalize_book_spine,
    _normalize_chapters,
    _normalize_domain,
)
from app.domain.course_from_article.common.content.textutil import _as_str, _slug, _string_list
from app.domain.course_from_article.curriculum.outline.chapter_budget import (
    chapter_ceiling,
    corpus_char_count,
)
from app.domain.course_from_article.curriculum.outline.course_locale import normalize_course_locale
from app.domain.course_from_article.local_course.curriculum.spine import merge_book_spine
from app.domain.course_from_article.pack.assemble_manifest import align_chapter_ids_to_topic_keys
from app.domain.course_from_article.pack.source_images import attach_source_images_to_chapters
from app.domain.course_from_article.workflow.events.progress import _band_progress, _stage_event
from app.domain.course_from_article.workflow.pipeline.pipeline_hooks import _stage_json
from app.domain.errors import TutorError
from app.domain.llm.transport.retry import should_retry_json_error
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


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


@dataclass(frozen=True)
class AnalyzeOutline:
    analysis: dict[str, Any]
    chapters: list[dict[str, str]]
    outcomes: list[str]
    domain: str
    pack_id: str
    title: str
    locale: str
    book_spine: dict[str, str]


def _analyze_outline_max_tokens(*, compact: bool, chapter_cap: int) -> int:
    per_chapter = 55 if compact else 90
    base = 900 if compact else 2400
    ceiling = 2800 if compact else 12_000
    return min(ceiling, base + max(1, chapter_cap) * per_chapter)


def _fullness_warning(*, got: int, wanted: int) -> str:
    return f"sources supported {got} of {wanted} requested theory slides"


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
    safe_detail = {key: value for key, value in detail.items() if key != "id"}
    merged = _normalize_chapters([{**chapter, **safe_detail, "id": chapter["id"]}])
    return merged[0] if merged else chapter


def _seal_analyze_chapters(
    enriched: list[dict[str, str]],
    *,
    sources: list[dict[str, object]],
    skeleton: list[dict[str, str]],
) -> list[dict[str, str]]:
    normalized = _normalize_chapters(enriched) or enriched
    aligned = align_chapter_ids_to_topic_keys(normalized)
    for index, chapter in enumerate(aligned):
        if index < len(skeleton):
            skeleton[index] = {"id": chapter["id"], "title": chapter["title"]}
    return attach_source_images_to_chapters(aligned, sources)


async def _request_outline(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    article: str,
    sources: list[dict[str, object]],
    chapter_cap: int,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    analysis: dict[str, Any] = {}
    chapters: list[dict[str, str]] = []
    for attempt in range(3):
        try:
            analysis = await _stage_json(
                client,
                target,
                compact=compact,
                stage="analyze",
                user_message=_analyze_user_message(body, article, sources=sources, compact=compact),
                max_tokens=_analyze_outline_max_tokens(compact=compact, chapter_cap=chapter_cap),
            )
        except TutorError as exc:
            if not should_retry_json_error(exc, attempt=attempt, attempts=3):
                raise
            continue
        chapters = _normalize_chapters(analysis.get("chapters"))
        if chapters:
            return analysis, chapters
    raise TutorError(status.HTTP_502_BAD_GATEWAY, "course analyze returned no chapters")


def _build_outline(
    analysis: dict[str, Any],
    chapters: list[dict[str, str]],
    *,
    body: CourseFromArticleRequest,
    article: str,
    chapter_cap: int,
    result: AnalyzeStageResult,
) -> AnalyzeOutline:
    wanted = body.effective_theory_count()
    if len(chapters) > chapter_cap:
        result.warning = f"trimmed chapters to {chapter_cap}"
        chapters = chapters[:chapter_cap]
    elif wanted is not None and len(chapters) < min(wanted, chapter_cap):
        result.warning = _fullness_warning(got=len(chapters), wanted=min(wanted, chapter_cap))
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
    book_spine = merge_book_spine(
        _normalize_book_spine(analysis.get("book_spine")),
        locale=locale,
        title=title,
        chapters=chapters,
        outcomes=outcomes,
    )
    return AnalyzeOutline(
        analysis=analysis,
        chapters=chapters,
        outcomes=outcomes,
        domain=domain,
        pack_id=pack_id,
        title=title,
        locale=locale,
        book_spine=book_spine,
    )


async def _iter_chapter_enrichment(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    article: str,
    sources: list[dict[str, object]],
    outline: AnalyzeOutline,
    band_analyze: tuple[float, float],
    skeleton: list[dict[str, str]],
    enriched: list[dict[str, str]],
) -> AsyncIterator[dict[str, object]]:
    units = 1 + len(outline.chapters)
    total = len(outline.chapters)
    for index, chapter in enumerate(outline.chapters):
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
            outcomes=outline.outcomes,
        )
        enriched.append(enriched_chapter)
        skeleton[index] = {
            "id": enriched_chapter["id"],
            "title": enriched_chapter["title"],
        }


def _assign_analyze_result(
    result: AnalyzeStageResult,
    outline: AnalyzeOutline,
    *,
    chapters: list[dict[str, str]],
) -> None:
    result.chapters = chapters
    result.book_spine = outline.book_spine
    result.outcomes = outline.outcomes
    result.domain = outline.domain
    result.course_profile = (
        _as_str(outline.analysis.get("course_profile"))
        or _as_str(outline.analysis.get("domain_profile"))
        or ""
    )
    result.pack_id = outline.pack_id
    result.title = outline.title
    result.locale = outline.locale


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
    hard_max = _MAX_CHAPTERS_COMPACT if compact else _MAX_CHAPTERS
    chapter_cap = chapter_ceiling(
        body,
        corpus_chars=corpus_char_count(sources, article),
        hard_max=hard_max,
    )
    analysis, chapters = await _request_outline(
        client,
        target,
        body=body,
        compact=compact,
        article=article,
        sources=sources,
        chapter_cap=chapter_cap,
    )
    outline = _build_outline(
        analysis,
        chapters,
        body=body,
        article=article,
        chapter_cap=chapter_cap,
        result=result,
    )
    units = 1 + len(outline.chapters)
    skeleton = [{"id": c["id"], "title": c["title"]} for c in outline.chapters]
    yield _stage_event(
        stage="analyze",
        status="running",
        progress=_band_progress(band_analyze, 1, units),
        message="Syllabus outline ready — enriching chapters",
        message_key="analyzeOutlineReady",
        detail={
            "title": outline.title,
            "pack_id": outline.pack_id,
            "domain": outline.domain,
            "outcomes": outline.outcomes,
            "chapters": skeleton,
            "chapter_count": len(outline.chapters),
            "phase": "enrich",
        },
    )
    enriched: list[dict[str, str]] = []
    async for event in _iter_chapter_enrichment(
        client,
        target,
        body=body,
        compact=compact,
        article=article,
        sources=sources,
        outline=outline,
        band_analyze=band_analyze,
        skeleton=skeleton,
        enriched=enriched,
    ):
        yield event
    sealed = _seal_analyze_chapters(enriched, sources=sources, skeleton=skeleton)
    _assign_analyze_result(result, outline, chapters=sealed)
    yield _stage_event(
        stage="analyze",
        status="done",
        progress=band_analyze[1],
        message="Outline ready",
        message_key="analyzeDone",
        detail={
            "title": outline.title,
            "pack_id": outline.pack_id,
            "domain": outline.domain,
            "outcomes": outline.outcomes,
            "chapters": skeleton,
            "chapter_count": len(result.chapters),
            "has_book_spine": bool(
                outline.book_spine.get("throughline") or outline.book_spine.get("voice")
            ),
        },
    )
