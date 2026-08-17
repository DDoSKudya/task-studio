from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from app.config import TutorConfig
from app.domain.course_build import CourseBuildMeta, CourseBuildStore
from app.domain.course_from_article.common.content.constants import (
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
from app.domain.course_from_article.common.content.textutil import (
    _articles_from_body,
    _combined_corpus,
    _video_steps_from_sources,
)
from app.domain.course_from_article.common.runtime.course_context import (
    set_course_parts,
    set_course_profile,
    set_strategy_pack,
)
from app.domain.course_from_article.common.runtime.provider_policy import (
    CourseHarnessPolicy,
    course_harness_policy,
)
from app.domain.course_from_article.curriculum.outline.course_locale import normalize_course_locale
from app.domain.course_from_article.curriculum.outline.course_profile import (
    CourseProfile,
    normalize_course_profile,
)
from app.domain.course_from_article.curriculum.theory.theory_split import split_long_theory_steps
from app.domain.course_from_article.local_course import iter_local_course_content
from app.domain.course_from_article.practice.pipeline_code_suitability import (
    CodeSuitabilityResult,
    iter_code_suitability_stage,
)
from app.domain.course_from_article.practice.practice_routing import (
    infer_course_runtime,
    should_use_open_practice,
)
from app.domain.course_from_article.practice.source_exercise_harvest import (
    HarvestedExercise,
    exercises_from_checkpoint,
    exercises_to_checkpoint,
    harvest_sources,
)
from app.domain.course_from_article.quality.final_quality import apply_final_course_quality
from app.domain.course_from_article.quality.polish import _iter_book_polish
from app.domain.course_from_article.workflow.events.progress import _stage_event
from app.domain.course_from_article.workflow.pipeline.pipeline_analyze import (
    AnalyzeStageResult,
    iter_analyze_stage,
)
from app.domain.course_from_article.workflow.pipeline.pipeline_assemble import iter_assemble_stage
from app.domain.course_from_article.workflow.pipeline.pipeline_checkpoint import emit_build_event
from app.domain.course_from_article.workflow.pipeline.pipeline_content import (
    ContentStageResult,
    iter_content_stages,
)
from app.domain.course_from_article.workflow.pipeline.pipeline_hooks import (
    _fetch_user_settings,
    _resolve_llm_target,
)
from app.domain.course_from_article.workflow.stages.topic_bundles import (
    TopicBundleResult,
    iter_topic_bundle_stages,
)
from app.domain.errors import TutorError
from app.domain.llm.content.prose_dedupe import dedupe_theory_steps_across_course
from app.domain.llm.target import LlmTarget
from app.domain.ollama.runtime_policy import OllamaProfile, OllamaRuntimePolicy
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

logger = logging.getLogger(__name__)


def _ollama_runtime_for_config(config: TutorConfig) -> OllamaRuntimePolicy:
    from app.domain.ollama.runtime_policy import OllamaRuntimePolicy, load_ollama_runtime_policy

    runtime = getattr(config, "ollama_runtime", None)
    if isinstance(runtime, OllamaRuntimePolicy):
        return runtime
    return load_ollama_runtime_policy(
        fallback_model=getattr(config, "ollama_model", "") or "",
    )


@dataclass(frozen=True)
class ProgressBands:
    analyze: tuple[float, float]
    theory: tuple[float, float]
    polish: tuple[float, float]
    quizzes: tuple[float, float]
    code: tuple[float, float]
    assemble: tuple[float, float]


@dataclass
class ContentBuckets:
    theory: list[dict[str, object]] = field(default_factory=list)
    quizzes: list[dict[str, object]] = field(default_factory=list)
    codes: list[dict[str, object]] = field(default_factory=list)


def progress_bands(*, multi: bool, body: CourseFromArticleRequest) -> ProgressBands:
    bands = _allocate_progress_bands(
        include_theory=bool(body.include_theory),
        include_quizzes=bool(body.include_quizzes),
        include_code=bool(body.include_code),
    )
    return ProgressBands(
        analyze=bands["analyze"],
        theory=bands.get("theory", _BAND_THEORY if multi else _BAND_THEORY_SOLO),
        polish=bands.get("polish", _BAND_POLISH if multi else _BAND_POLISH_SOLO),
        quizzes=bands.get("quizzes", _BAND_QUIZZES if multi else _BAND_QUIZZES_SOLO),
        code=bands.get("code", _BAND_CODE if multi else _BAND_CODE_SOLO),
        assemble=bands["assemble"],
    )


def restore_outline_from_checkpoint(
    saved: dict[str, object],
    *,
    body: CourseFromArticleRequest,
    build_meta: CourseBuildMeta,
    outline: AnalyzeStageResult,
) -> list[HarvestedExercise] | None:
    chapters_raw = saved.get("chapters")
    outline.chapters = [
        {str(key): str(value) for key, value in item.items()}
        for item in (chapters_raw if isinstance(chapters_raw, list) else [])
        if isinstance(item, dict)
    ]
    spine = saved.get("book_spine")
    outline.book_spine = (
        {str(key): str(value) for key, value in spine.items()} if isinstance(spine, dict) else {}
    )
    outcomes_raw = saved.get("outcomes")
    outline.outcomes = (
        [str(item) for item in outcomes_raw] if isinstance(outcomes_raw, list) else []
    )
    outline.domain = str(saved.get("domain") or "general")
    outline.course_profile = str(saved.get("course_profile") or "")
    outline.pack_id = str(saved.get("pack_id") or "article-course")
    outline.title = str(saved.get("title") or build_meta.title)
    outline.locale = normalize_course_locale(body.locale)
    return exercises_from_checkpoint(saved.get("exercise_seeds"))


def save_outline_checkpoint(
    store: CourseBuildStore,
    *,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    outline: AnalyzeStageResult,
    exercise_seeds: list[HarvestedExercise],
    build_meta: CourseBuildMeta,
) -> None:
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


def practice_flags(
    *,
    body: CourseFromArticleRequest,
    open_practice: bool,
    action: str | None,
) -> tuple[bool, bool]:
    if (open_practice and body.include_code) or action == "open_tasks":
        return False, True
    if action == "no_practice":
        return False, False
    if action == "keep_code":
        return True, False
    return bool(body.include_code), False


def body_after_practice_gate(
    body: CourseFromArticleRequest,
    *,
    use_code: bool,
    use_open: bool,
) -> CourseFromArticleRequest:
    if use_code:
        return body
    if use_open:
        if body.include_code:
            return body
        return body.model_copy(update={"include_code": True})
    if body.include_code:
        return body.model_copy(update={"include_code": False})
    return body


def codes_for_practice_mode(
    steps: list[dict[str, object]],
    *,
    use_open: bool,
    default_runtime: str = "",
) -> list[dict[str, object]]:
    if not use_open:
        return steps
    from app.domain.course_from_article.practice.normalize_practice import (
        _open_task_from_code_shim,
    )

    opened: list[dict[str, object]] = []
    for index, step in enumerate(steps):
        runtime = str(step.get("runtime") or default_runtime or "").strip()
        if str(step.get("kind") or "") == "task":
            if runtime and not step.get("runtime"):
                step = {**step, "runtime": runtime}
            opened.append(step)
            continue
        opened_step = _open_task_from_code_shim(
            task_id=str(step.get("id") or f"task-{index + 1}"),
            level=str(step.get("level") or "medium"),
            title=str(step.get("title") or "Task"),
            content=str(step.get("content") or ""),
            rubric=str(step.get("rubric") or step.get("content") or ""),
            runtime=runtime,
        )
        if chapter_id := step.get("chapter_id"):
            opened_step["chapter_id"] = chapter_id
        opened.append(opened_step)
    return opened


def apply_outline_profile(
    outline: AnalyzeStageResult,
    *,
    body: CourseFromArticleRequest,
    article: str,
    warnings: list[str],
) -> tuple[CourseFromArticleRequest, CourseProfile, bool, str, str]:
    outline.locale = normalize_course_locale(body.locale)
    course_profile = normalize_course_profile(
        outline.course_profile,
        domain=outline.domain,
        title=outline.title,
        corpus=article,
    )
    outline.course_profile = course_profile
    set_course_profile(course_profile)
    inferred_runtime, inferred_version = infer_course_runtime(
        title=outline.title,
        corpus=article,
        fallback=body.runtime,
    )
    body = body.model_copy(
        update={"runtime": inferred_runtime, "runtime_version": inferred_version}
    )
    open_practice = should_use_open_practice(
        title=outline.title,
        corpus=article,
        domain=outline.domain,
        profile=course_profile,
    )
    if open_practice:
        warnings.append("practice: open tasks (not a code editor)")
    return body, course_profile, open_practice, inferred_runtime, inferred_version


def resolve_code_suitability_body(
    body: CourseFromArticleRequest,
    *,
    open_practice: bool,
    saved_analyze: dict[str, object] | None,
) -> CourseFromArticleRequest:
    saved_action = (
        saved_analyze.get("code_suitability_action") if isinstance(saved_analyze, dict) else None
    )
    if body.code_suitability_action is None and isinstance(saved_action, str):
        body = body.model_copy(update={"code_suitability_action": saved_action})
    if open_practice and body.include_code and body.code_suitability_action is None:
        body = body.model_copy(update={"code_suitability_action": "open_tasks"})
    return body


async def iter_outline_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    article: str,
    sources: list[dict[str, object]],
    band_analyze: tuple[float, float],
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    build_meta: CourseBuildMeta,
    resumed: bool,
    exercise_seeds: list[HarvestedExercise],
    warnings: list[str],
    outline: AnalyzeStageResult,
    local_compiler: bool = False,
    ollama_profile: OllamaProfile = "cpu-light",
) -> AsyncIterator[dict[str, object]]:
    saved_analyze = store.load_analyze(user_id, build_id) if resumed else None
    if isinstance(saved_analyze, dict) and saved_analyze.get("chapters"):
        restored = restore_outline_from_checkpoint(
            saved_analyze,
            body=body,
            build_meta=build_meta,
            outline=outline,
        )
        if restored:
            exercise_seeds[:] = restored
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
        return

    if local_compiler:
        from app.domain.course_from_article.local_course.curriculum.compiler import (
            iter_local_outline_stage,
        )
        from app.domain.llm.target import LlmTarget

        if not isinstance(target, LlmTarget):
            msg = "ollama local outline requires LlmTarget"
            raise TypeError(msg)
        async for event in iter_local_outline_stage(
            client,
            target,
            body=body,
            article=article,
            sources=sources,
            band_analyze=band_analyze,
            store=store,
            user_id=user_id,
            build_id=build_id,
            build_meta=build_meta,
            exercise_seeds=exercise_seeds,
            warnings=warnings,
            outline=outline,
            ollama_profile=ollama_profile,
        ):
            yield event
        return

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
    save_outline_checkpoint(
        store,
        user_id=user_id,
        build_id=build_id,
        outline=outline,
        exercise_seeds=exercise_seeds,
        build_meta=build_meta,
    )


async def iter_code_gate(
    *,
    body: CourseFromArticleRequest,
    course_profile: CourseProfile,
    band_analyze: tuple[float, float],
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    result: CodeSuitabilityResult,
) -> AsyncIterator[dict[str, object]]:
    band_code_gate = (band_analyze[1], band_analyze[1] + 0.01)
    async for event in iter_code_suitability_stage(
        body=body,
        profile=course_profile,
        band=band_code_gate,
        result=result,
    ):
        yield event
    if result.halted:
        return
    if result.action:
        analyze_payload = store.load_analyze(user_id, build_id) or {}
        analyze_payload["code_suitability_action"] = result.action
        store.save_analyze(user_id, build_id, analyze_payload)


async def iter_polish_after_bundles(
    client: httpx.AsyncClient,
    target: object,
    *,
    harness: CourseHarnessPolicy,
    config: TutorConfig,
    body: CourseFromArticleRequest,
    chapters: list[dict[str, str]],
    book_spine: dict[str, str],
    band_polish: tuple[float, float],
    theory_steps: list[dict[str, object]],
) -> AsyncIterator[dict[str, object]]:
    ollama_profile = _ollama_runtime_for_config(config).profile
    run_polish = body.include_theory and len(theory_steps) >= 1 and harness.run_polish
    if run_polish:
        polish_compact = False if ollama_profile.startswith("gpu-") else harness.compact
        async for event in _iter_book_polish(
            client,
            target,
            body=body,
            compact=polish_compact,
            chapters=chapters,
            book_spine=book_spine,
            band_polish=band_polish,
            theory_steps=theory_steps,
        ):
            yield event


@dataclass(frozen=True)
class ContentRun:
    client: httpx.AsyncClient
    target: object
    config: TutorConfig
    harness: CourseHarnessPolicy
    body: CourseFromArticleRequest
    chapters: list[dict[str, str]]
    outcomes: list[str]
    book_spine: dict[str, str]
    domain: str
    use_code: bool
    use_open: bool
    open_practice: bool
    bands: ProgressBands
    warnings: list[str]
    store: CourseBuildStore
    user_id: uuid.UUID
    build_id: uuid.UUID
    exercise_seeds: list[HarvestedExercise]
    buckets: ContentBuckets
    article: str
    sources: list[dict[str, object]]


def _bundle_band(body: CourseFromArticleRequest, bands: ProgressBands) -> tuple[float, float]:
    return (
        bands.theory[0] if body.include_theory else bands.quizzes[0],
        bands.code[1] if body.include_code else bands.quizzes[1],
    )


async def _iter_local_content(run: ContentRun) -> AsyncIterator[dict[str, object]]:
    from app.domain.llm.target import LlmTarget as RuntimeLlmTarget

    if not isinstance(run.target, RuntimeLlmTarget):
        msg = "ollama local course requires LlmTarget"
        raise TypeError(msg)
    body = body_after_practice_gate(
        run.body,
        use_code=run.use_code,
        use_open=run.use_open,
    )
    bundle = TopicBundleResult()
    runtime = _ollama_runtime_for_config(run.config)
    async for event in iter_local_course_content(
        run.client,
        run.target,
        body=body,
        chapters=run.chapters,
        outcomes=run.outcomes,
        article=run.article,
        sources=run.sources,
        ollama_profile=runtime.profile,
        band=_bundle_band(body, run.bands),
        warnings=run.warnings,
        result=bundle,
        store=run.store,
        user_id=run.user_id,
        build_id=run.build_id,
        web_glossary=bool(getattr(run.config, "course_web_glossary", False)),
        web_allowlist=tuple(getattr(run.config, "course_web_allowlist", ()) or ()),
        exercise_seeds=run.exercise_seeds,
        book_spine=run.book_spine,
    ):
        yield event
    run.buckets.theory = bundle.theory_steps
    run.buckets.quizzes = bundle.quiz_steps
    run.buckets.codes = codes_for_practice_mode(
        bundle.code_steps,
        use_open=run.use_open,
        default_runtime=str(
            getattr(body, "runtime", None) or getattr(run.body, "runtime", None) or ""
        ),
    )
    if run.harness.run_polish and not local_course_skips_polish(run.target.model, runtime.profile):
        async for event in iter_polish_after_bundles(
            run.client,
            run.target,
            harness=run.harness,
            config=run.config,
            body=body,
            chapters=run.chapters,
            book_spine=run.book_spine,
            band_polish=run.bands.polish,
            theory_steps=run.buckets.theory,
        ):
            yield event
    run.buckets.theory = split_long_theory_steps(
        run.buckets.theory,
        enabled=run.harness.split_long_theory and run.body.split_long_theory,
        max_parts=3,
    )


async def _iter_topic_content(run: ContentRun) -> AsyncIterator[dict[str, object]]:
    body = body_after_practice_gate(
        run.body,
        use_code=run.use_code,
        use_open=run.use_open,
    )
    bundle = TopicBundleResult()
    async for event in iter_topic_bundle_stages(
        run.client,
        run.target,
        body=body,
        harness=run.harness,
        chapters=run.chapters,
        outcomes=run.outcomes,
        book_spine=run.book_spine,
        domain=run.domain,
        use_code=run.use_code,
        use_open=run.use_open,
        band=_bundle_band(body, run.bands),
        warnings=run.warnings,
        result=bundle,
        store=run.store,
        user_id=run.user_id,
        build_id=run.build_id,
        exercise_seeds=run.exercise_seeds,
    ):
        yield event
    run.buckets.theory = bundle.theory_steps
    run.buckets.quizzes = bundle.quiz_steps
    run.buckets.codes = bundle.code_steps
    async for event in iter_polish_after_bundles(
        run.client,
        run.target,
        harness=run.harness,
        config=run.config,
        body=body,
        chapters=run.chapters,
        book_spine=run.book_spine,
        band_polish=run.bands.polish,
        theory_steps=run.buckets.theory,
    ):
        yield event


async def _iter_phased_content(run: ContentRun) -> AsyncIterator[dict[str, object]]:
    content = ContentStageResult()
    body = body_after_practice_gate(
        run.body,
        use_code=run.use_code,
        use_open=run.use_open,
    )
    async for event in iter_content_stages(
        run.client,
        run.target,
        body=body,
        harness=run.harness,
        chapters=run.chapters,
        outcomes=run.outcomes,
        book_spine=run.book_spine,
        domain=run.domain,
        band_theory=run.bands.theory,
        band_polish=run.bands.polish,
        band_quizzes=run.bands.quizzes,
        band_code=run.bands.code,
        warnings=run.warnings,
        result=content,
        use_code=run.use_code,
        use_open=run.use_open,
        practice_is_open=run.open_practice,
        store=run.store,
        user_id=run.user_id,
        build_id=run.build_id,
        exercise_seeds=run.exercise_seeds,
    ):
        yield event
    run.buckets.theory = split_long_theory_steps(
        content.theory_steps,
        enabled=run.harness.split_long_theory and run.body.split_long_theory,
        max_parts=3,
    )
    run.buckets.quizzes = content.quiz_steps
    run.buckets.codes = content.code_steps


async def iter_bundle_or_phased_content(
    client: httpx.AsyncClient,
    target: object,
    config: TutorConfig,
    *,
    harness: CourseHarnessPolicy,
    body: CourseFromArticleRequest,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    domain: str,
    use_code: bool,
    use_open: bool,
    open_practice: bool,
    bands: ProgressBands,
    warnings: list[str],
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    exercise_seeds: list[HarvestedExercise],
    buckets: ContentBuckets,
    article: str = "",
    sources: list[dict[str, object]] | None = None,
) -> AsyncIterator[dict[str, object]]:
    run = ContentRun(
        client=client,
        target=target,
        config=config,
        harness=harness,
        body=body,
        chapters=chapters,
        outcomes=outcomes,
        book_spine=book_spine,
        domain=domain,
        use_code=use_code,
        use_open=use_open,
        open_practice=open_practice,
        bands=bands,
        warnings=warnings,
        store=store,
        user_id=user_id,
        build_id=build_id,
        exercise_seeds=exercise_seeds,
        buckets=buckets,
        article=article,
        sources=sources or [],
    )
    if harness.provider == "ollama":
        iterator = _iter_local_content(run)
    elif body.uses_topic_bundles():
        iterator = _iter_topic_content(run)
    else:
        iterator = _iter_phased_content(run)
    async for event in iterator:
        yield event


def local_course_skips_polish(model: str, profile: OllamaProfile) -> bool:
    from app.domain.course_from_article.local_course import local_course_policy_for

    return not local_course_policy_for(profile=profile, model=model).run_polish


@dataclass
class PipelineBootstrap:
    target: object
    harness: CourseHarnessPolicy
    sources: list[dict[str, object]]
    exercise_seeds: list[HarvestedExercise]
    article: str
    warnings: list[str]
    multi: bool
    bands: ProgressBands

    @property
    def compact(self) -> bool:
        return self.harness.compact


async def _ensure_course_model(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    runtime: OllamaRuntimePolicy,
    provider_url: str | None,
) -> tuple[list[str] | None, bool, str]:
    from app.domain.ollama.ensure_models import list_ollama_models, pull_ollama_model
    from app.domain.ollama.model_select import resolve_task_model
    from app.domain.ollama.runtime_policy import model_for_task

    wanted = model_for_task(runtime, "course_topic_bundle")
    if not config.ollama_url or provider_url:
        return None, False, wanted
    try:
        installed = await list_ollama_models(client, ollama_url=config.ollama_url)
    except httpx.HTTPError as exc:
        raise TutorError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ollama is not reachable. Start Ollama, then retry the course build.",
        ) from exc
    resolved, model_fallback = resolve_task_model(
        runtime,
        "course_topic_bundle",
        installed=installed,
    )
    if resolved is None:
        try:
            await pull_ollama_model(client, ollama_url=config.ollama_url, model=wanted)
            installed = await list_ollama_models(client, ollama_url=config.ollama_url)
        except httpx.HTTPError:
            pass
        resolved, model_fallback = resolve_task_model(
            runtime,
            "course_topic_bundle",
            installed=installed,
        )
    if resolved is None:
        raise TutorError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ollama is missing a course-capable model (minimum qwen2.5:7b; "
            "qwen2.5:3b is not suitable). "
            f"Pull {wanted} (qwen2.5:3b for CPU or qwen2.5:7b for GPU), "
            "then retry the course build.",
        )
    return installed, model_fallback, wanted


def _runtime_warnings(
    *,
    harness: CourseHarnessPolicy,
    runtime: OllamaRuntimePolicy,
    target: LlmTarget,
    model_fallback: bool,
) -> list[str]:
    from app.domain.ollama.runtime_policy import model_for_task

    if harness.provider != "ollama":
        return [f"strategy_pack={harness.strategy_pack} provider={harness.provider}"]
    mode = "compact" if harness.compact else "full"
    pipeline_line = (
        f"course pipeline mode={mode} profile={runtime.profile} "
        f"model={target.model} strategy_pack={harness.strategy_pack} "
        f"split_long_theory={harness.split_long_theory} "
        f"theory_max_continues={harness.theory_max_continues} "
        f"sectional_theory={harness.sectional_theory} "
        f"theory_quality_rounds={harness.theory_quality_rounds} "
        f"quiz_quality_rounds={harness.quiz_quality_rounds} "
        f"practice_quality_rounds={harness.practice_quality_rounds}"
    )
    warnings = [pipeline_line]
    logger.info(pipeline_line)
    if model_fallback:
        wanted = model_for_task(runtime, "course_topic_bundle")
        fallback_line = (
            f"course model fallback: using {target.model!r} instead of {wanted!r} "
            "(pull the profile model for better quality)"
        )
        warnings.append(fallback_line)
        logger.info(fallback_line)
    return warnings


async def bootstrap_course_pipeline(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
    active_model: list[str],
) -> PipelineBootstrap:
    runtime = _ollama_runtime_for_config(config)
    user_settings = await _fetch_user_settings(client, config, user_id)
    from app.domain.llm.target import course_provider_url

    provider_url = course_provider_url(
        config,
        provider_url=user_settings.provider_url,
        active_provider=getattr(user_settings, "active_provider", None),
    )
    installed, model_fallback, wanted_course = await _ensure_course_model(
        client,
        config,
        runtime=runtime,
        provider_url=provider_url,
    )
    target = _resolve_llm_target(
        config,
        provider_url=provider_url,
        api_key_encrypted=user_settings.api_key_encrypted,
        model=user_settings.model,
        task="course_topic_bundle",
        installed_models=installed,
    )
    if target is None:
        if config.ollama_url and not provider_url:
            raise TutorError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                f"Ollama model {wanted_course!r} is not installed. "
                "Pull it first, then retry the course build.",
            )
        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no tutor provider configured")
    active_model.clear()
    active_model.append(target.model)

    harness = course_harness_policy(
        config,
        target,
        ollama_profile=runtime.profile,
    )
    set_strategy_pack(harness.strategy_pack)
    compact = harness.compact
    sources, exercise_seeds = harvest_sources(_articles_from_body(body))
    article = _combined_corpus(sources, compact=compact)
    warnings = _runtime_warnings(
        harness=harness,
        runtime=runtime,
        target=target,
        model_fallback=model_fallback,
    )
    if exercise_seeds:
        warnings.append(
            f"harvested {len(exercise_seeds)} article exercise/quiz block(s) "
            "for assess/practice (kept out of theory)"
        )
    multi = len(sources) > 1
    return PipelineBootstrap(
        target=target,
        harness=harness,
        sources=sources,
        exercise_seeds=exercise_seeds,
        article=article,
        warnings=warnings,
        multi=multi,
        bands=progress_bands(multi=multi, body=body),
    )


async def _iter_finalize_course(
    *,
    body: CourseFromArticleRequest,
    boot: PipelineBootstrap,
    outline: AnalyzeStageResult,
    buckets: ContentBuckets,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    runtime: str,
    runtime_version: str,
) -> AsyncIterator[dict[str, object]]:
    apply_final_course_quality(
        chapters=outline.chapters,
        theory_steps=buckets.theory,
        quizzes=buckets.quizzes,
        practices=buckets.codes,
        sources=boot.sources,
        strategy_pack=boot.harness.strategy_pack,
        warnings=boot.warnings,
        store=store,
        user_id=user_id,
        build_id=build_id,
    )
    stripped = dedupe_theory_steps_across_course(buckets.theory)
    if stripped:
        boot.warnings.append(f"theory: stripped repeated long sentences from {stripped} chapter(s)")
    async for event in iter_assemble_stage(
        pack_id=outline.pack_id,
        title=outline.title,
        locale=outline.locale,
        runtime=runtime,
        runtime_version=runtime_version,
        theory_steps=buckets.theory,
        video_steps=_video_steps_from_sources(boot.sources),
        quiz_steps=buckets.quizzes,
        code_steps=buckets.codes,
        chapters=outline.chapters,
        outcomes=outline.outcomes,
        warnings=boot.warnings,
        deviations=[],
        sources_count=len(boot.sources),
        band_assemble=boot.bands.assemble,
        interleaved=body.uses_topic_bundles() and bool(outline.chapters),
    ):
        yield event


def _start_pipeline(
    body: CourseFromArticleRequest,
    build_meta: CourseBuildMeta,
) -> tuple[uuid.UUID, list[dict[str, object]]]:
    set_course_parts(
        theory=body.include_theory,
        quizzes=body.include_quizzes,
        practice=body.include_code,
    )
    return uuid.UUID(build_meta.build_id), [
        emit_build_event(build_meta),
        _stage_event(
            stage="analyze",
            status="running",
            progress=0.02,
            message="Preparing course model",
            message_key="analyzePreparing",
        ),
    ]


async def iter_course_pipeline_body(
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
    build_id, start_events = _start_pipeline(body, build_meta)
    for event in start_events:
        yield event
    boot = await bootstrap_course_pipeline(
        client,
        config,
        user_id=user_id,
        body=body,
        active_model=active_model,
    )

    outline = AnalyzeStageResult()
    async for event in iter_outline_stage(
        client,
        boot.target,
        body=body,
        compact=boot.compact,
        article=boot.article,
        sources=boot.sources,
        band_analyze=boot.bands.analyze,
        store=store,
        user_id=user_id,
        build_id=build_id,
        build_meta=build_meta,
        resumed=resumed,
        exercise_seeds=boot.exercise_seeds,
        warnings=boot.warnings,
        outline=outline,
        local_compiler=boot.harness.provider == "ollama",
        ollama_profile=_ollama_runtime_for_config(config).profile,
    ):
        yield event

    body, course_profile, open_practice, inferred_runtime, inferred_version = apply_outline_profile(
        outline,
        body=body,
        article=boot.article,
        warnings=boot.warnings,
    )
    saved_analyze = store.load_analyze(user_id, build_id) if resumed else None
    body = resolve_code_suitability_body(
        body,
        open_practice=open_practice,
        saved_analyze=saved_analyze if isinstance(saved_analyze, dict) else None,
    )
    code_gate = CodeSuitabilityResult()
    async for event in iter_code_gate(
        body=body,
        course_profile=course_profile,
        band_analyze=boot.bands.analyze,
        store=store,
        user_id=user_id,
        build_id=build_id,
        result=code_gate,
    ):
        yield event
    if code_gate.halted:
        return

    use_code, use_open = practice_flags(
        body=body,
        open_practice=open_practice,
        action=code_gate.action,
    )
    set_course_parts(
        theory=body.include_theory,
        quizzes=body.include_quizzes,
        practice=use_code or use_open,
    )
    buckets = ContentBuckets()
    async for event in iter_bundle_or_phased_content(
        client,
        boot.target,
        config,
        harness=boot.harness,
        body=body,
        chapters=outline.chapters,
        outcomes=outline.outcomes,
        book_spine=outline.book_spine,
        domain=outline.domain,
        use_code=use_code,
        use_open=use_open,
        open_practice=open_practice,
        bands=boot.bands,
        warnings=boot.warnings,
        store=store,
        user_id=user_id,
        build_id=build_id,
        exercise_seeds=boot.exercise_seeds,
        buckets=buckets,
        article=boot.article,
        sources=boot.sources,
    ):
        yield event

    async for event in _iter_finalize_course(
        body=body,
        boot=boot,
        outline=outline,
        buckets=buckets,
        store=store,
        user_id=user_id,
        build_id=build_id,
        runtime=inferred_runtime,
        runtime_version=inferred_version,
    ):
        yield event
