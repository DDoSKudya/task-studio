from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

import httpx
from app.config import TutorConfig
from app.domain.course_build import CourseBuildMeta, CourseBuildStore
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
from .course_context import set_course_profile
from .course_locale import normalize_course_locale
from .course_profile import normalize_course_profile
from .pipeline_analyze import AnalyzeStageResult, iter_analyze_stage
from .pipeline_assemble import iter_assemble_stage
from .pipeline_checkpoint import (
    emit_build_event,
    mark_build_done,
    mark_build_paused,
    resolve_build_session,
    sync_progress_from_event,
)
from .pipeline_code_suitability import CodeSuitabilityResult, iter_code_suitability_stage
from .pipeline_consistency import ConsistencyStageResult, iter_consistency_stage
from .pipeline_content import ContentStageResult, iter_content_stages
from .pipeline_hooks import (
    _fetch_user_settings,
    _is_ollama_target,
    _resolve_llm_target,
)
from .practice_routing import infer_course_runtime, should_use_open_practice
from .source_exercise_harvest import (
    exercises_from_checkpoint,
    exercises_to_checkpoint,
    harvest_sources,
)
from .textutil import (
    _articles_from_body,
    _combined_corpus,
    _video_steps_from_sources,
)
from .theory_split import split_long_theory_steps
from .topic_bundles import TopicBundleResult, iter_topic_bundle_stages


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
        if event.get("type") == "code_suitability_gate":
            raise TutorError(
                status.HTTP_409_CONFLICT,
                "code task suitability requires confirmation "
                "(set code_suitability_action to continue)",
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
    from .stream_keepalive import iter_course_sse_with_pings

    async for frame in iter_course_sse_with_pings(
        iter_course_from_article(client, config, user_id=user_id, body=body)
    ):
        yield frame


async def iter_course_from_article(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> AsyncIterator[dict[str, object]]:
    store, build_meta, body, resumed = resolve_build_session(config, user_id=user_id, body=body)
    build_id = uuid.UUID(build_meta.build_id)
    active_model: list[str] = []

    def _pause(message: str, *, failed: bool = False) -> None:
        mark_build_paused(
            store,
            user_id=user_id,
            build_id=build_id,
            message=message,
            failed=failed,
        )

    async def _stop_local_inference() -> None:
        if not config.ollama_url:
            return
        model = (active_model[0] if active_model else "") or config.ollama_model
        if not model:
            return
        from app.domain.ollama.stop import stop_ollama_model

        await stop_ollama_model(client, ollama_url=config.ollama_url, model=model)

    try:
        async for event in _iter_course_from_article_body(
            client,
            config,
            user_id=user_id,
            body=body,
            store=store,
            build_meta=build_meta,
            resumed=resumed,
            active_model=active_model,
        ):
            event_type = event.get("type")
            if event_type in {"stage", "consistency_gate", "code_suitability_gate"}:
                sync_progress_from_event(store, user_id=user_id, build_id=build_id, event=event)
            if event_type in {"consistency_gate", "code_suitability_gate"}:
                _pause(str(event.get("message") or "Waiting for confirmation"))
            if event_type == "error":
                _pause(str(event.get("message") or "course generation failed"), failed=True)
            if event_type == "done":
                mark_build_done(store, user_id=user_id, build_id=build_id)
                detail = event.setdefault("detail", {})
                if isinstance(detail, dict):
                    detail["build_id"] = str(build_id)
                else:
                    event["detail"] = {"build_id": str(build_id)}
                event["build_id"] = str(build_id)
            yield event
    except asyncio.CancelledError:
        _pause("Cancelled by user", failed=False)
        await _stop_local_inference()
        raise
    except TutorError as exc:
        _pause(str(exc.detail), failed=exc.status_code >= 500)
        raise
    except Exception as exc:
        _pause(str(exc) or "course generation failed", failed=True)
        raise


async def _iter_course_from_article_body(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
    store: CourseBuildStore,
    build_meta: CourseBuildMeta,
    resumed: bool,
    active_model: list[str],
) -> AsyncIterator[dict[str, object]]:
    build_id = uuid.UUID(build_meta.build_id)

    yield emit_build_event(build_meta)

    user_settings = await _fetch_user_settings(client, config, user_id)
    target = _resolve_llm_target(
        config,
        provider_url=user_settings.provider_url,
        api_key_encrypted=user_settings.api_key_encrypted,
        model=user_settings.model,
        task="course_topic_bundle",
    )
    if target is None:
        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no tutor provider configured")
    active_model.clear()
    active_model.append(target.model)

    compact = _is_ollama_target(config, target)
    raw_sources = _articles_from_body(body)
    sources, exercise_seeds = harvest_sources(raw_sources)
    article = _combined_corpus(sources, compact=compact)
    warnings: list[str] = []
    deviations: list[CourseDeviation] = []
    multi = len(sources) > 1
    if exercise_seeds:
        warnings.append(
            f"harvested {len(exercise_seeds)} article exercise/quiz block(s) "
            "for assess/practice (kept out of theory)"
        )
    bands = _allocate_progress_bands(
        multi_article=multi,
        include_theory=bool(body.include_theory),
        include_quizzes=bool(body.include_quizzes),
        include_code=bool(body.include_code),
    )
    band_analyze = bands["analyze"]
    band_theory = bands.get("theory", _BAND_THEORY if multi else _BAND_THEORY_SOLO)
    band_polish = bands.get("polish", _BAND_POLISH if multi else _BAND_POLISH_SOLO)
    band_quizzes = bands.get("quizzes", _BAND_QUIZZES if multi else _BAND_QUIZZES_SOLO)
    band_code = bands.get("code", _BAND_CODE if multi else _BAND_CODE_SOLO)
    band_assemble = bands["assemble"]

    if multi and not (resumed and store.load_analyze(user_id, build_id)):
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
    saved_analyze = store.load_analyze(user_id, build_id) if resumed else None
    if isinstance(saved_analyze, dict) and saved_analyze.get("chapters"):
        outline.chapters = [
            {str(k): str(v) for k, v in item.items()}
            for item in saved_analyze["chapters"]
            if isinstance(item, dict)
        ]
        spine = saved_analyze.get("book_spine")
        outline.book_spine = (
            {str(k): str(v) for k, v in spine.items()} if isinstance(spine, dict) else {}
        )
        outcomes_raw = saved_analyze.get("outcomes")
        outline.outcomes = (
            [str(item) for item in outcomes_raw] if isinstance(outcomes_raw, list) else []
        )
        outline.domain = str(saved_analyze.get("domain") or "general")
        outline.course_profile = str(saved_analyze.get("course_profile") or "")
        outline.pack_id = str(saved_analyze.get("pack_id") or "article-course")
        outline.title = str(saved_analyze.get("title") or build_meta.title)
        outline.locale = normalize_course_locale(body.locale)
        restored_seeds = exercises_from_checkpoint(saved_analyze.get("exercise_seeds"))
        if restored_seeds:
            exercise_seeds = restored_seeds
        yield {
            "type": "stage",
            "stage": "analyze",
            "status": "done",
            "progress": band_analyze[1],
            "message": "Outline restored from checkpoint",
            "message_key": "analyzeRestored",
            "detail": {
                "build_id": str(build_id),
                "restored": True,
                "chapters": len(outline.chapters),
            },
        }
    else:
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
        outline.locale = normalize_course_locale(body.locale)
        store.save_analyze(
            user_id,
            build_id,
            {
                "chapters": outline.chapters,
                "book_spine": outline.book_spine,
                "outcomes": outline.outcomes,
                "domain": outline.domain,
                "course_profile": outline.course_profile,
                "pack_id": outline.pack_id,
                "title": outline.title,
                "locale": outline.locale,
                "exercise_seeds": exercises_to_checkpoint(exercise_seeds),
            },
        )
        store.patch_meta(
            user_id,
            build_id,
            title=outline.title or build_meta.title,
            stage="analyze",
            chapter_total=len(outline.chapters),
            clear_error=True,
        )

    locale = normalize_course_locale(body.locale)
    outline.locale = locale
    chapters = outline.chapters
    book_spine = outline.book_spine
    outcomes = outline.outcomes
    domain = outline.domain
    pack_id = outline.pack_id
    title = outline.title
    course_profile = normalize_course_profile(
        outline.course_profile,
        domain=domain,
        title=title,
        corpus=article,
    )
    set_course_profile(course_profile)

    inferred_runtime, inferred_version = infer_course_runtime(
        title=title,
        corpus=article,
        fallback=body.runtime,
    )
    body = body.model_copy(
        update={"runtime": inferred_runtime, "runtime_version": inferred_version}
    )
    open_practice = should_use_open_practice(title=title, corpus=article, domain=domain)
    if open_practice:
        warnings.append(
            "practice: open tasks (CLI/DevOps — commands and configs, not a code editor)"
        )

    code_gate = CodeSuitabilityResult()
    band_code_gate = (band_analyze[1], band_analyze[1] + 0.01)
    saved_action = None
    if isinstance(saved_analyze, dict):
        saved_action = saved_analyze.get("code_suitability_action")
    if body.code_suitability_action is None and isinstance(saved_action, str):
        body = body.model_copy(update={"code_suitability_action": saved_action})
    if open_practice and body.include_code and body.code_suitability_action is None:
        body = body.model_copy(update={"code_suitability_action": "open_tasks"})

    async for event in iter_code_suitability_stage(
        body=body,
        profile=course_profile,
        band=band_code_gate,
        result=code_gate,
    ):
        yield event
    if code_gate.halted:
        return
    if code_gate.action:
        analyze_payload = store.load_analyze(user_id, build_id) or {}
        analyze_payload["code_suitability_action"] = code_gate.action
        store.save_analyze(user_id, build_id, analyze_payload)

    use_code = bool(body.include_code)
    use_open = False
    action = code_gate.action
    if (open_practice and body.include_code) or action == "open_tasks":
        use_code = False
        use_open = True
    elif action == "no_practice":
        use_code = False
        use_open = False
    elif action == "keep_code":
        use_code = True

    content_theory: list[dict[str, object]] = []
    content_quizzes: list[dict[str, object]] = []
    content_codes: list[dict[str, object]] = []

    if body.uses_topic_bundles():
        bundle_band = (
            band_theory[0] if body.include_theory else band_quizzes[0],
            band_code[1] if body.include_code else band_quizzes[1],
        )
        bundle = TopicBundleResult()
        async for event in iter_topic_bundle_stages(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            book_spine=book_spine,
            domain=domain,
            use_code=use_code,
            use_open=use_open,
            band=bundle_band,
            warnings=warnings,
            result=bundle,
            store=store,
            user_id=user_id,
            build_id=build_id,
            exercise_seeds=exercise_seeds,
        ):
            yield event
        content_theory = bundle.theory_steps
        content_quizzes = bundle.quiz_steps
        content_codes = bundle.code_steps
        # Book polish is another full pass per chapter — skip on local Ollama.
        if body.include_theory and len(content_theory) >= 2 and not compact:
            from .polish import _iter_book_polish

            async for event in _iter_book_polish(
                client,
                target,
                body=body,
                compact=compact,
                chapters=chapters,
                book_spine=book_spine,
                band_polish=band_polish,
                theory_steps=content_theory,
                warnings=warnings,
            ):
                yield event
        elif body.include_theory and compact and content_theory:
            warnings.append("book polish skipped for local model (speed)")
            yield {
                "type": "stage",
                "stage": "polish",
                "status": "done",
                "progress": band_polish[1],
                "message": "Book polish skipped for local model",
                "message_key": "polishSkippedLocal",
                "detail": {"skipped": True, "reason": "compact"},
            }
    else:
        content = ContentStageResult()
        effective_body = body
        if not use_code and use_open:
            effective_body = body.model_copy(update={"include_code": True})
        elif not use_code and body.include_code:
            effective_body = body.model_copy(update={"include_code": False})
        async for event in iter_content_stages(
            client,
            target,
            body=effective_body,
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
            use_code=use_code,
            use_open=use_open,
            practice_is_open=open_practice,
            store=store,
            user_id=user_id,
            build_id=build_id,
            exercise_seeds=exercise_seeds,
        ):
            yield event
        content_theory = split_long_theory_steps(
            content.theory_steps,
            enabled=body.split_long_theory,
        )
        content_quizzes = content.quiz_steps
        content_codes = content.code_steps
    video_steps = _video_steps_from_sources(sources)

    async for event in iter_assemble_stage(
        pack_id=pack_id,
        title=title,
        locale=locale,
        runtime=inferred_runtime,
        runtime_version=inferred_version,
        theory_steps=content_theory,
        video_steps=video_steps,
        quiz_steps=content_quizzes,
        code_steps=content_codes,
        chapters=chapters,
        outcomes=outcomes,
        warnings=warnings,
        deviations=deviations,
        sources_count=len(sources),
        band_assemble=band_assemble,
        interleaved=body.uses_topic_bundles() and bool(chapters),
    ):
        yield event
