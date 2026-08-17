from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from functools import partial

import httpx
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.curriculum.theory.theory_sections import theory_chapter_digest
from app.domain.course_from_article.local_course.content.topic_loop import (
    generate_topic_practice,
    generate_topic_quizzes,
    generate_topic_theory,
    quiz_is_compiled_fallback,
)
from app.domain.course_from_article.local_course.integrations.web_glossary import (
    GlossaryLookups,
    append_external_note,
    lookup_chapter_note,
)
from app.domain.course_from_article.local_course.policy.heuristics import (
    practice_spec_is_usable,
    quiz_item_is_usable,
)
from app.domain.course_from_article.local_course.policy.policy import LocalCoursePolicy
from app.domain.course_from_article.local_course.runtime.stage_retry import retry_local_stage
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_from_article.quality.chapter_quality import theory_content_is_usable
from app.domain.course_from_article.workflow.events.progress import _band_progress, _stage_event
from app.domain.course_from_article.workflow.stages.topic_bundles import TopicBundleResult
from app.domain.llm.target import LlmTarget
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


def _theory_from_saved(saved: dict[str, object]) -> list[dict[str, object]]:
    theories = saved.get("theories")
    if isinstance(theories, list) and theories:
        return [item for item in theories if isinstance(item, dict)]
    step = saved.get("theory")
    return [step] if isinstance(step, dict) else []


def _list_from_saved(saved: dict[str, object], key: str) -> list[dict[str, object]]:
    rows = saved.get(key)
    if not isinstance(rows, list):
        return []
    return [item for item in rows if isinstance(item, dict)]


def _stamp_chapter_id(steps: list[dict[str, object]], chapter_id: str) -> None:
    for step in steps:
        step["chapter_id"] = chapter_id


def _checkpoint_topic(
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    chapter_id: str,
    *,
    theories: list[dict[str, object]],
    quizzes: list[dict[str, object]],
    codes: list[dict[str, object]],
) -> None:
    store.save_topic(
        user_id,
        build_id,
        chapter_id,
        theories=theories,
        quizzes=quizzes,
        codes=codes,
    )


def _quiz_checkpoint(
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    chapter_id: str,
    theories: list[dict[str, object]],
    codes: list[dict[str, object]],
) -> Callable[[list[dict[str, object]]], None]:
    def persist(rows: list[dict[str, object]]) -> None:
        _checkpoint_topic(
            store, user_id, build_id, chapter_id, theories=theories, quizzes=rows, codes=codes
        )

    return persist


def _practice_checkpoint(
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    chapter_id: str,
    theories: list[dict[str, object]],
    quizzes: list[dict[str, object]],
) -> Callable[[list[dict[str, object]]], None]:
    def persist(rows: list[dict[str, object]]) -> None:
        _checkpoint_topic(
            store, user_id, build_id, chapter_id, theories=theories, quizzes=quizzes, codes=rows
        )

    return persist


def restored_topic_event(
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    topic_key: str,
    saved: dict[str, object],
    quiz_n: int,
    practice_n: int,
    index: int,
    topic_total: int,
    band: tuple[float, float],
    result: TopicBundleResult,
    topic_ready: Callable[..., bool],
) -> dict[str, object] | None:
    theory_steps = _theory_from_saved(saved)
    topic_quizzes = _list_from_saved(saved, "quizzes")
    topic_codes = _list_from_saved(saved, "codes")
    if not topic_ready(
        body,
        theory_steps=theory_steps,
        quizzes=topic_quizzes,
        codes=topic_codes,
        quiz_n=quiz_n,
        practice_n=practice_n,
        excerpt=chapter.get("source_excerpt") or "",
    ):
        return None
    kept_quizzes = topic_quizzes[:quiz_n]
    kept_codes = topic_codes[:practice_n]
    _stamp_chapter_id(theory_steps, topic_key)
    _stamp_chapter_id(kept_quizzes, topic_key)
    _stamp_chapter_id(kept_codes, topic_key)
    result.theory_steps.extend(theory_steps)
    result.quiz_steps.extend(kept_quizzes)
    result.code_steps.extend(kept_codes)
    digest = ""
    if theory_steps:
        digest = theory_chapter_digest(str(theory_steps[-1].get("content") or ""))
    event = _stage_event(
        stage="topic_bundle",
        status="done",
        progress=_band_progress(band, index + 1, topic_total),
        message=f"Topic restored: {chapter['title']}",
        message_key="topicBundleRestored",
        message_params={"title": chapter["title"]},
        index=index + 1,
        total=topic_total,
        detail={"chapter_id": chapter["id"], "restored": True},
    )
    event["_prior_digest"] = digest
    return event


async def build_topic_theory(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    chapters: list[dict[str, str]],
    index: int,
    article: str,
    sources: list[dict[str, object]],
    policy: LocalCoursePolicy,
    spine: dict[str, str],
    previous_digest: str,
    saved: dict[str, object] | None,
    glossary: GlossaryLookups,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    topic_key: str,
    restored_quizzes: list[dict[str, object]],
    restored_codes: list[dict[str, object]],
    quiz_n: int,
    practice_n: int,
) -> list[dict[str, object]]:
    theory_steps: list[dict[str, object]] = []
    if not body.include_theory and (quiz_n or practice_n):
        stub = (chapter.get("source_excerpt") or "").strip() or " ".join(
            part for part in (chapter.get("title"), chapter.get("objective")) if part
        ).strip()
        if stub:
            theory_steps = [{"content": stub, "title": chapter["title"]}]
    if not body.include_theory:
        return theory_steps

    restored_theory = _theory_from_saved(saved) if isinstance(saved, dict) else []
    theory_ok = any(theory_content_is_usable(step.get("content")) for step in restored_theory)
    if theory_ok:
        theory_steps = restored_theory
    else:
        theory = await retry_local_stage(
            partial(
                generate_topic_theory,
                client,
                target,
                body=body,
                chapter=chapter,
                policy=policy,
                prior_chapter_digest=previous_digest,
                article=article,
                book_spine=spine,
                next_title=(chapters[index + 1]["title"] if index + 1 < len(chapters) else ""),
                store=store,
                user_id=user_id,
                build_id=build_id,
            ),
            retries=policy.stage_retries,
            label="theory",
            title=chapter["title"],
        )
        if policy.web_glossary:
            note = await lookup_chapter_note(
                client,
                chapter=chapter,
                sources=sources,
                article=article,
                lookups=glossary,
            )
            if note:
                theory = {
                    **theory,
                    "content": append_external_note(str(theory.get("content") or ""), note),
                }
        theory_steps = [theory]
    _stamp_chapter_id(theory_steps, topic_key)
    _checkpoint_topic(
        store,
        user_id,
        build_id,
        topic_key,
        theories=theory_steps,
        quizzes=restored_quizzes,
        codes=restored_codes,
    )
    store.discard_section_drafts(user_id, build_id, topic_key)
    return theory_steps


async def build_topic_quizzes(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    theory_steps: list[dict[str, object]],
    quiz_n: int,
    policy: LocalCoursePolicy,
    topic_key: str,
    warnings: list[str],
    restored_quizzes: list[dict[str, object]],
    restored_codes: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None,
    previous_digest: str,
    result: TopicBundleResult,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    index: int,
    topic_total: int,
) -> list[dict[str, object]]:
    if quiz_n <= 0 or not theory_steps:
        return []
    theory_blob = str(theory_steps[0].get("content") or "")
    kept_quizzes = [
        item
        for item in restored_quizzes
        if quiz_item_is_usable(item, theory=theory_blob, locale=body.locale)
    ]
    persist_quizzes = _quiz_checkpoint(
        store,
        user_id,
        build_id,
        topic_key,
        theory_steps,
        restored_codes,
    )
    topic_quizzes = await retry_local_stage(
        partial(
            generate_topic_quizzes,
            client,
            target,
            body=body,
            chapter=chapter,
            theory=theory_steps[0],
            count=quiz_n,
            policy=policy,
            topic_key=topic_key,
            warnings=warnings,
            already=kept_quizzes,
            persist=persist_quizzes,
            exercise_seeds=exercise_seeds,
            prior_digest=previous_digest,
            course_already_questions=[
                str(item.get("question") or "")
                for item in result.quiz_steps
                if not quiz_is_compiled_fallback(item)
            ],
            chapter_index=index,
            chapter_total=topic_total,
        ),
        retries=policy.stage_retries,
        label="quizzes",
        title=chapter["title"],
    )
    _stamp_chapter_id(topic_quizzes, topic_key)
    persist_quizzes(topic_quizzes)
    return topic_quizzes


async def build_topic_practice(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    theory_steps: list[dict[str, object]],
    practice_n: int,
    policy: LocalCoursePolicy,
    topic_key: str,
    warnings: list[str],
    restored_codes: list[dict[str, object]],
    topic_quizzes: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
) -> list[dict[str, object]]:
    if practice_n <= 0 or not theory_steps:
        return []
    theory_blob = str(theory_steps[0].get("content") or "")
    kept_codes = [
        item
        for item in restored_codes
        if practice_spec_is_usable(item, locale=body.locale, theory=theory_blob)
    ]
    persist_codes = _practice_checkpoint(
        store,
        user_id,
        build_id,
        topic_key,
        theory_steps,
        topic_quizzes,
    )
    topic_codes = await retry_local_stage(
        partial(
            generate_topic_practice,
            client,
            target,
            body=body,
            chapter=chapter,
            theory=theory_steps[0],
            count=practice_n,
            policy=policy,
            topic_key=topic_key,
            warnings=warnings,
            already=kept_codes,
            persist=persist_codes,
            exercise_seeds=exercise_seeds,
        ),
        retries=policy.stage_retries,
        label="practice",
        title=chapter["title"],
    )
    _stamp_chapter_id(topic_codes, topic_key)
    return topic_codes


async def _generate_one_topic(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    chapters: list[dict[str, str]],
    index: int,
    topic_total: int,
    article: str,
    sources: list[dict[str, object]],
    policy: LocalCoursePolicy,
    spine: dict[str, str],
    glossary: GlossaryLookups,
    warnings: list[str],
    result: TopicBundleResult,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    topic_key: str,
    saved: dict[str, object] | None,
    quiz_n: int,
    practice_n: int,
    previous_digest: str,
    exercise_seeds: list[HarvestedExercise] | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], str]:
    restored_quizzes = _list_from_saved(saved, "quizzes") if saved else []
    restored_codes = _list_from_saved(saved, "codes") if saved else []
    theory_steps = await build_topic_theory(
        client,
        target,
        body=body,
        chapter=chapter,
        chapters=chapters,
        index=index,
        article=article,
        sources=sources,
        policy=policy,
        spine=spine,
        previous_digest=previous_digest,
        saved=saved,
        glossary=glossary,
        store=store,
        user_id=user_id,
        build_id=build_id,
        topic_key=topic_key,
        restored_quizzes=restored_quizzes,
        restored_codes=restored_codes,
        quiz_n=quiz_n,
        practice_n=practice_n,
    )
    next_digest = previous_digest
    if body.include_theory and theory_steps:
        result.theory_steps.extend(theory_steps)
        next_digest = theory_chapter_digest(str(theory_steps[-1].get("content") or ""))

    topic_quizzes = await build_topic_quizzes(
        client,
        target,
        body=body,
        chapter=chapter,
        theory_steps=theory_steps,
        quiz_n=quiz_n,
        policy=policy,
        topic_key=topic_key,
        warnings=warnings,
        restored_quizzes=restored_quizzes,
        restored_codes=restored_codes,
        exercise_seeds=exercise_seeds,
        previous_digest=previous_digest,
        result=result,
        store=store,
        user_id=user_id,
        build_id=build_id,
        index=index,
        topic_total=topic_total,
    )
    result.quiz_steps.extend(topic_quizzes)

    topic_codes = await build_topic_practice(
        client,
        target,
        body=body,
        chapter=chapter,
        theory_steps=theory_steps,
        practice_n=practice_n,
        policy=policy,
        topic_key=topic_key,
        warnings=warnings,
        restored_codes=restored_codes,
        topic_quizzes=topic_quizzes,
        exercise_seeds=exercise_seeds,
        store=store,
        user_id=user_id,
        build_id=build_id,
    )
    result.code_steps.extend(topic_codes)
    _stamp_chapter_id(theory_steps, topic_key)
    _stamp_chapter_id(topic_quizzes, topic_key)
    _stamp_chapter_id(topic_codes, topic_key)
    _checkpoint_topic(
        store,
        user_id,
        build_id,
        topic_key,
        theories=theory_steps,
        quizzes=topic_quizzes,
        codes=topic_codes,
    )
    return theory_steps, topic_quizzes, topic_codes, next_digest


async def iter_built_topics(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapters: list[dict[str, str]],
    article: str,
    sources: list[dict[str, object]],
    policy: LocalCoursePolicy,
    spine: dict[str, str],
    glossary: GlossaryLookups,
    band: tuple[float, float],
    warnings: list[str],
    result: TopicBundleResult,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    topic_keys: list[str],
    quiz_total: int,
    practice_total: int,
    exercise_seeds: list[HarvestedExercise] | None,
    topic_ready: Callable[..., bool],
    share_count: Callable[[int, int, int], int],
) -> AsyncIterator[dict[str, object]]:
    topic_total = max(1, len(chapters))
    per_topic = body.uses_topic_bundles()
    prior_digest = ""

    for index, chapter in enumerate(chapters):
        topic_key = topic_keys[index] if index < len(topic_keys) else chapter["id"]
        quiz_n = quiz_total if per_topic else share_count(quiz_total, topic_total, index)
        practice_n = (
            practice_total if per_topic else share_count(practice_total, topic_total, index)
        )
        saved_raw = store.load_topic(user_id, build_id, topic_key)
        saved = saved_raw if isinstance(saved_raw, dict) else None
        if saved is not None:
            restored = restored_topic_event(
                body=body,
                chapter=chapter,
                topic_key=topic_key,
                saved=saved,
                quiz_n=quiz_n,
                practice_n=practice_n,
                index=index,
                topic_total=topic_total,
                band=band,
                result=result,
                topic_ready=topic_ready,
            )
            if restored is not None:
                prior_digest = str(restored.pop("_prior_digest", "") or prior_digest)
                yield restored
                continue

        yield _stage_event(
            stage="topic_bundle",
            status="running",
            progress=_band_progress(band, index, topic_total),
            message=f"Building topic: {chapter['title']}",
            message_key="topicBundleRunning",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=topic_total,
            detail={"chapter_id": chapter["id"], "chapter_title": chapter["title"]},
        )
        _, _, _, prior_digest = await _generate_one_topic(
            client,
            target,
            body=body,
            chapter=chapter,
            chapters=chapters,
            index=index,
            topic_total=topic_total,
            article=article,
            sources=sources,
            policy=policy,
            spine=spine,
            glossary=glossary,
            warnings=warnings,
            result=result,
            store=store,
            user_id=user_id,
            build_id=build_id,
            topic_key=topic_key,
            saved=saved,
            quiz_n=quiz_n,
            practice_n=practice_n,
            previous_digest=prior_digest,
            exercise_seeds=exercise_seeds,
        )
        yield _stage_event(
            stage="topic_bundle",
            status="done",
            progress=_band_progress(band, index + 1, topic_total),
            message=f"Topic ready: {chapter['title']}",
            message_key="topicBundleReady",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=topic_total,
            detail={"chapter_id": chapter["id"]},
        )
