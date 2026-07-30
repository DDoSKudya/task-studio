from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
from app.config import TutorConfig
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import (
    CourseDeviation,
    CourseFromArticleMeta,
    CourseFromArticleRequest,
    CourseFromArticleResponse,
)

from .constants import (
    _BAND_CODE,
    _BAND_CODE_SOLO,
    _BAND_POLISH,
    _BAND_POLISH_SOLO,
    _BAND_QUIZZES,
    _BAND_QUIZZES_SOLO,
    _BAND_THEORY,
    _BAND_THEORY_SOLO,
    _allocate_progress_bands,
)
from .pipeline_analyze import AnalyzeStageResult, iter_analyze_stage
from .pipeline_assemble import iter_assemble_stage
from .pipeline_consistency import ConsistencyStageResult, iter_consistency_stage
from .pipeline_content import ContentStageResult, iter_content_stages
from .pipeline_hooks import (
    _fetch_user_settings,
    _is_ollama_target,
    _resolve_llm_target,
)
from .progress import _sse_event
from .textutil import (
    _articles_from_body,
    _combined_corpus,
    _video_steps_from_sources,
)


async def generate_course_from_article(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> CourseFromArticleResponse:
    final: CourseFromArticleResponse | None = None
    async for event in iter_course_from_article(client, config, user_id=user_id, body=body):
        if event.get("type") == "consistency_gate":
            raise TutorError(
                status.HTTP_409_CONFLICT,
                "article deviations require confirmation (set ignore_deviations=true to continue)",
            )
        if event.get("type") == "error":
            code = event.get("status_code")
            status_code = code if isinstance(code, int) else status.HTTP_502_BAD_GATEWAY
            raise TutorError(
                status_code,
                str(event.get("message") or "course generation failed"),
            )
        if event.get("type") == "done":
            manifest = event.get("manifest")
            meta_raw = event.get("meta")
            if not isinstance(manifest, dict):
                raise TutorError(
                    status.HTTP_502_BAD_GATEWAY, "course generation returned no manifest"
                )
            meta = CourseFromArticleMeta.model_validate(meta_raw or {})
            final = CourseFromArticleResponse(manifest=manifest, meta=meta)
    if final is None:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course generation produced no result")
    return final


async def stream_course_from_article(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> AsyncIterator[bytes]:
    try:
        async for event in iter_course_from_article(client, config, user_id=user_id, body=body):
            yield _sse_event(event)
    except TutorError as exc:
        yield _sse_event(
            {
                "type": "error",
                "stage": "failed",
                "status": "error",
                "progress": 0.0,
                "message": exc.detail,
                "status_code": exc.status_code,
            }
        )
    except Exception as exc:  # noqa: BLE001 — SSE boundary
        yield _sse_event(
            {
                "type": "error",
                "stage": "failed",
                "status": "error",
                "progress": 0.0,
                "message": str(exc) or "course generation failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }
        )


async def iter_course_from_article(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> AsyncIterator[dict[str, object]]:
    user_settings = await _fetch_user_settings(client, config, user_id)
    target = _resolve_llm_target(
        config,
        provider_url=user_settings.provider_url,
        api_key_encrypted=user_settings.api_key_encrypted,
        model=user_settings.model,
    )
    if target is None:
        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no tutor provider configured")

    compact = _is_ollama_target(config, target)
    sources = _articles_from_body(body)
    article = _combined_corpus(sources)
    warnings: list[str] = []
    deviations: list[CourseDeviation] = []
    multi = len(sources) > 1
    bands = _allocate_progress_bands(
        multi_article=multi,
        include_theory=bool(body.include_theory),
        include_quizzes=bool(body.include_quizzes),
        include_code=bool(body.include_code),
    )
    band_analyze = bands["analyze"]
    band_theory = bands.get("theory", _BAND_THEORY_SOLO if not multi else _BAND_THEORY)
    band_polish = bands.get("polish", _BAND_POLISH_SOLO if not multi else _BAND_POLISH)
    band_quizzes = bands.get("quizzes", _BAND_QUIZZES_SOLO if not multi else _BAND_QUIZZES)
    band_code = bands.get("code", _BAND_CODE_SOLO if not multi else _BAND_CODE)
    band_assemble = bands["assemble"]

    if multi:
        consistency = ConsistencyStageResult()
        async for event in iter_consistency_stage(
            client,
            target,
            body=body,
            compact=compact,
            sources=sources,
            result=consistency,
            band_consistency=bands["consistency"],
        ):
            yield event
        if consistency.halted:
            return
        deviations = consistency.deviations
        if consistency.warning:
            warnings.append(consistency.warning)

    outline = AnalyzeStageResult()
    async for event in iter_analyze_stage(
        client,
        target,
        body=body,
        compact=compact,
        article=article,
        sources=sources,
        band_analyze=band_analyze,
        result=outline,
    ):
        yield event
    if outline.warning:
        warnings.append(outline.warning)
    chapters = outline.chapters
    book_spine = outline.book_spine
    outcomes = outline.outcomes
    domain = outline.domain
    pack_id = outline.pack_id
    title = outline.title
    locale = outline.locale

    content = ContentStageResult()
    async for event in iter_content_stages(
        client,
        target,
        body=body,
        compact=compact,
        chapters=chapters,
        outcomes=outcomes,
        book_spine=book_spine,
        domain=domain,
        band_theory=band_theory,
        band_polish=band_polish,
        band_quizzes=band_quizzes,
        band_code=band_code,
        warnings=warnings,
        result=content,
    ):
        yield event
    video_steps = _video_steps_from_sources(sources)

    async for event in iter_assemble_stage(
        pack_id=pack_id,
        title=title,
        locale=locale,
        runtime=body.runtime,
        runtime_version=body.runtime_version,
        theory_steps=content.theory_steps,
        video_steps=video_steps,
        quiz_steps=content.quiz_steps,
        code_steps=content.code_steps,
        chapters=chapters,
        outcomes=outcomes,
        warnings=warnings,
        deviations=deviations,
        sources_count=len(sources),
        band_assemble=band_assemble,
    ):
        yield event
