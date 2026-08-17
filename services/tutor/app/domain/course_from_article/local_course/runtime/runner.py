from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.common.runtime.course_context import (
    set_course_parts,
    set_strategy_pack,
)
from app.domain.course_from_article.curriculum.outline.course_locale import normalize_course_locale
from app.domain.course_from_article.local_course.curriculum.compiler import (
    compile_local_syllabus,
    localize_chapter_labels,
)
from app.domain.course_from_article.local_course.curriculum.outline import (
    chapter_titles_are_unique,
    reject_duplicate_titles,
    syllabus_has_excerpts,
)
from app.domain.course_from_article.local_course.curriculum.spine import merge_book_spine
from app.domain.course_from_article.local_course.policy.heuristics import (
    practice_spec_is_usable,
    quiz_item_is_usable,
    theory_copies_excerpt,
)
from app.domain.course_from_article.local_course.policy.policy import (
    LocalCoursePolicy,
    local_course_policy_for,
)
from app.domain.course_from_article.local_course.runtime.runner_topics import (
    _stamp_chapter_id as _stamp_chapter_id,
)
from app.domain.course_from_article.local_course.runtime.runner_topics import iter_built_topics
from app.domain.course_from_article.pack.assemble_manifest import _topic_keys
from app.domain.course_from_article.pack.source_images import attach_source_images_to_chapters
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_from_article.quality.chapter_quality import theory_content_is_usable
from app.domain.course_from_article.workflow.stages.topic_bundles import TopicBundleResult
from app.domain.course_strategies import blocks_from_sources, build_course_blueprints
from app.domain.errors import TutorError
from app.domain.llm.target import LlmTarget
from app.domain.ollama.quality_lang import needs_quality_retry
from app.domain.ollama.runtime_policy import OllamaProfile
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


def apply_local_scale(
    body: CourseFromArticleRequest,
    policy: LocalCoursePolicy,
) -> CourseFromArticleRequest:
    _ = policy
    return body


def requested_assess_counts(body: CourseFromArticleRequest) -> tuple[int, int]:
    quizzes = body.effective_quiz_count() if body.include_quizzes else 0
    practice = body.effective_practice_count() if body.include_code else 0
    return quizzes, practice


def _share_count(total: int, buckets: int, index: int) -> int:
    if total <= 0 or buckets <= 0:
        return 0
    base, extra = divmod(total, buckets)
    return base + (1 if index < extra else 0)


async def ensure_local_chapters(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    article: str,
    sources: list[dict[str, object]],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    policy: LocalCoursePolicy,
    warnings: list[str],
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
) -> tuple[list[dict[str, str]], list[str]]:
    cleaned = reject_duplicate_titles(chapters)
    if cleaned and chapter_titles_are_unique(cleaned) and syllabus_has_excerpts(cleaned):
        dropped = len(chapters) - len(cleaned)
        if dropped > 0:
            warnings.append(
                f"local outline: dropped {dropped} near-duplicate chapter(s), kept {len(cleaned)}"
            )
        return await localize_chapter_labels(
            client,
            target,
            body=body,
            chapters=cleaned,
            outcomes=outcomes,
            policy=policy,
        )
    compiled, compiled_outcomes = await compile_local_syllabus(
        client,
        target,
        body=body,
        sources=sources,
        article=article,
        policy=policy,
        store=store,
        user_id=user_id,
        build_id=build_id,
        warnings=warnings,
    )
    if compiled and syllabus_has_excerpts(compiled):
        return compiled, compiled_outcomes or outcomes
    raise TutorError(
        status.HTTP_502_BAD_GATEWAY,
        "local syllabus has no teachable chapter excerpts",
    )


def _local_topic_ready(
    body: CourseFromArticleRequest,
    *,
    theory_steps: list[dict[str, object]],
    quizzes: list[dict[str, object]],
    codes: list[dict[str, object]],
    quiz_n: int,
    practice_n: int,
    excerpt: str = "",
) -> bool:
    if body.include_theory:
        if not any(theory_content_is_usable(step.get("content")) for step in theory_steps):
            return False
        if excerpt and any(
            theory_copies_excerpt(step.get("content"), excerpt) for step in theory_steps
        ):
            return False
    theory_blob = str(theory_steps[0].get("content") or "") if theory_steps else ""
    locale = normalize_course_locale(body.locale)
    if body.include_theory and any(
        needs_quality_retry(str(step.get("content") or ""), locale) for step in theory_steps
    ):
        return False
    if quiz_n:
        grounded = [
            item for item in quizzes if quiz_item_is_usable(item, theory=theory_blob, locale=locale)
        ]
        if len(grounded) < quiz_n:
            return False
    if practice_n:
        usable = [
            item
            for item in codes
            if practice_spec_is_usable(item, locale=locale, theory=theory_blob)
        ]
        if len(usable) < practice_n:
            return False
    return True


async def iter_local_course_content(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    article: str,
    sources: list[dict[str, object]] | None = None,
    ollama_profile: OllamaProfile,
    band: tuple[float, float],
    warnings: list[str],
    result: TopicBundleResult,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    web_glossary: bool = False,
    web_allowlist: tuple[str, ...] = (),
    exercise_seeds: list[HarvestedExercise] | None = None,
    book_spine: dict[str, str] | None = None,
) -> AsyncIterator[dict[str, object]]:
    from app.domain.course_from_article.local_course.integrations.web_glossary import (
        DEFAULT_WEB_ALLOWLIST,
        MAX_GLOSSARY_FETCHES,
        GlossaryLookups,
    )
    from app.domain.course_from_article.local_course.policy.policy import (
        model_meets_course_minimum,
    )
    from app.domain.errors import TutorError
    from fastapi import status as http_status

    if not model_meets_course_minimum(target.model):
        raise TutorError(
            http_status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Course generation requires at least qwen2.5:7b; got {target.model!r}. "
            "Pull qwen2.5:3b for CPU or qwen2.5:7b for GPU, then retry.",
        )
    policy = local_course_policy_for(
        profile=ollama_profile,
        model=target.model,
        web_glossary=web_glossary,
    )
    set_strategy_pack(policy.strategy_pack)
    if policy.warning:
        warnings.append(policy.warning)
    scaled = apply_local_scale(body, policy)
    set_course_parts(
        theory=scaled.include_theory,
        quizzes=scaled.include_quizzes,
        practice=scaled.include_code,
    )
    glossary = GlossaryLookups(
        allowlist=web_allowlist or DEFAULT_WEB_ALLOWLIST,
        remaining=MAX_GLOSSARY_FETCHES if policy.web_glossary else 0,
    )
    chapters_out, outcomes_out = await ensure_local_chapters(
        client,
        target,
        body=scaled,
        article=article,
        sources=sources or [],
        chapters=chapters,
        outcomes=outcomes,
        policy=policy,
        warnings=warnings,
        store=store,
        user_id=user_id,
        build_id=build_id,
    )
    chapters_out = attach_source_images_to_chapters(chapters_out, sources or [])
    blueprints = build_course_blueprints(
        chapters_out,
        source_blocks=blocks_from_sources(sources or []),
    )
    store.save_blueprint(
        user_id,
        build_id,
        {
            "strategy_pack": policy.strategy_pack,
            "chapters": blueprints,
        },
    )
    chapters[:] = chapters_out
    outcomes[:] = outcomes_out
    spine = merge_book_spine(
        book_spine,
        locale=str(scaled.locale or "ru"),
        title=str(scaled.title or ""),
        chapters=chapters,
        outcomes=outcomes,
    )
    quiz_total, practice_total = requested_assess_counts(scaled)
    async for event in iter_built_topics(
        client,
        target,
        body=scaled,
        chapters=chapters,
        article=article,
        sources=sources or [],
        policy=policy,
        spine=spine,
        glossary=glossary,
        band=band,
        warnings=warnings,
        result=result,
        store=store,
        user_id=user_id,
        build_id=build_id,
        topic_keys=_topic_keys(chapters),
        quiz_total=quiz_total,
        practice_total=practice_total,
        exercise_seeds=exercise_seeds,
        topic_ready=_local_topic_ready,
        share_count=_share_count,
    ):
        yield event
