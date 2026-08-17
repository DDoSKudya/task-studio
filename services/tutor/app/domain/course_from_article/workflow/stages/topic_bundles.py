from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.common.runtime.provider_policy import CourseHarnessPolicy
from app.domain.course_from_article.curriculum.theory.theory_expand import (
    _expand_one_theory_chapter,
)
from app.domain.course_from_article.curriculum.theory.theory_sections import theory_chapter_digest
from app.domain.course_from_article.curriculum.theory.theory_split import split_long_theory_steps
from app.domain.course_from_article.pack.assemble_manifest import _topic_keys
from app.domain.course_from_article.practice.practice_generate import (
    generate_code_tasks,
    generate_open_tasks,
)
from app.domain.course_from_article.practice.quiz_generate import generate_quizzes
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_from_article.quality.assess_quality import quiz_is_usable
from app.domain.course_from_article.quality.chapter_quality import (
    reinforce_theory_chapter,
    theory_content_is_usable,
)
from app.domain.course_from_article.workflow.events.progress import _band_progress, _stage_event
from app.domain.llm.content.prose_dedupe import clean_theory_markdown
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


@dataclass
class TopicBundleResult:
    theory_steps: list[dict[str, object]] = field(default_factory=list)
    quiz_steps: list[dict[str, object]] = field(default_factory=list)
    code_steps: list[dict[str, object]] = field(default_factory=list)


def topic_bundle_complete(
    body: CourseFromArticleRequest,
    *,
    theory_steps: list[dict[str, object]],
    quizzes: list[dict[str, object]],
    codes: list[dict[str, object]],
    quiz_fail_soft: bool = False,
    expect_quizzes: bool | None = None,
    expect_codes: bool | None = None,
) -> bool:
    _ = quiz_fail_soft
    need_quizzes = expect_quizzes if expect_quizzes is not None else body.include_quizzes
    need_codes = expect_codes if expect_codes is not None else body.include_code
    theory_ok = (not body.include_theory) or _theory_steps_usable(theory_steps)
    quizzes_ok = (not need_quizzes) or any(quiz_is_usable(quiz) for quiz in quizzes)
    codes_ok = (not need_codes) or bool(codes)
    return theory_ok and quizzes_ok and codes_ok


def _theory_steps_usable(theory_steps: list[dict[str, object]]) -> bool:
    return any(theory_content_is_usable(step.get("content")) for step in theory_steps)


def _per_topic_counts(
    body: CourseFromArticleRequest,
    *,
    topic_total: int,
    topic_index: int = 0,
) -> tuple[int, int]:
    _ = topic_total, topic_index
    quizzes = body.effective_quiz_count() if body.include_quizzes else 0
    practice = body.effective_practice_count() if body.include_code else 0
    return quizzes, practice


def _ensure_distinct_titles(
    steps: list[dict[str, object]],
    *,
    fallback_keys: tuple[str, ...] = ("question", "content"),
) -> None:
    seen: dict[str, int] = {}
    for step in steps:
        title = str(step.get("title") or "").strip()
        if not title:
            for key in fallback_keys:
                if candidate := str(step.get(key) or "").strip():
                    title = candidate.split("\n", maxsplit=1)[0][:100]
                    break
            title = title or str(step.get("id") or "step")
            step["title"] = title
        key = title.casefold()
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            step["title"] = f"{title} ({count})"


def _namespace_step_id(step: dict[str, object], topic_key: str) -> None:
    raw = step.get("id")
    if not isinstance(raw, str) or not raw.strip():
        return
    step_id = raw.strip()
    prefix = f"{topic_key}--"
    if step_id.startswith(prefix):
        return
    step["id"] = f"{prefix}{step_id}"[:96]


def _theory_steps_from_saved(raw: dict[str, Any]) -> list[dict[str, object]]:
    theories = raw.get("theories")
    if isinstance(theories, list) and theories:
        return [_heal_theory_step(item) for item in theories if isinstance(item, dict)]
    step = raw.get("theory")
    return [_heal_theory_step(step)] if isinstance(step, dict) else []


def _heal_theory_step(step: dict[str, object]) -> dict[str, object]:
    content = step.get("content")
    if isinstance(content, str) and content.strip():
        step = {**step, "content": clean_theory_markdown(content)}
    return step


def _list_steps(raw: dict[str, Any], key: str) -> list[dict[str, object]]:
    rows = raw.get(key)
    if not isinstance(rows, list):
        return []
    return [item for item in rows if isinstance(item, dict)]


def _extend_restored_topic(
    result: TopicBundleResult,
    *,
    theory_steps: list[dict[str, object]],
    quizzes: list[dict[str, object]],
    codes: list[dict[str, object]],
) -> None:
    result.theory_steps.extend(theory_steps)
    result.quiz_steps.extend(quizzes)
    result.code_steps.extend(codes)


@dataclass
class TopicParts:
    theory: list[dict[str, object]] = field(default_factory=list)
    quizzes: list[dict[str, object]] = field(default_factory=list)
    codes: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class TopicBundleRun:
    client: httpx.AsyncClient
    target: object
    body: CourseFromArticleRequest
    harness: CourseHarnessPolicy
    chapters: list[dict[str, str]]
    outcomes: list[str]
    book_spine: dict[str, str]
    domain: str
    use_code: bool
    use_open: bool
    band: tuple[float, float]
    warnings: list[str]
    result: TopicBundleResult
    store: CourseBuildStore | None
    user_id: uuid.UUID | None
    build_id: uuid.UUID | None
    exercise_seeds: list[HarvestedExercise] | None


def _restore_topic(
    run: TopicBundleRun,
    *,
    chapter_id: str,
    saved_ids: set[str],
) -> TopicParts | None:
    if (
        chapter_id not in saved_ids
        or run.store is None
        or run.user_id is None
        or run.build_id is None
    ):
        return None
    saved = run.store.load_topic(run.user_id, run.build_id, chapter_id)
    if not isinstance(saved, dict):
        return None
    parts = TopicParts(
        theory=_theory_steps_from_saved(saved),
        quizzes=_list_steps(saved, "quizzes"),
        codes=_list_steps(saved, "codes"),
    )
    if not topic_bundle_complete(
        run.body,
        theory_steps=parts.theory,
        quizzes=parts.quizzes,
        codes=parts.codes,
        quiz_fail_soft=run.harness.quiz_fail_soft,
    ):
        return None
    _extend_restored_topic(
        run.result,
        theory_steps=parts.theory,
        quizzes=parts.quizzes,
        codes=parts.codes,
    )
    return parts


async def _iter_topic_theory(
    run: TopicBundleRun,
    *,
    chapter: dict[str, str],
    topic_key: str,
    index: int,
    prior_digests: list[str],
    parts: TopicParts,
) -> AsyncIterator[dict[str, object]]:
    if not run.body.include_theory:
        return
    section_events: list[dict[str, object]] = []

    async def on_section(section_index: int, section_count: int) -> None:
        section_events.append(
            _stage_event(
                stage="topic_bundle",
                status="running",
                progress=_band_progress(run.band, index, len(run.chapters)),
                message=f"Theory section {section_index}/{section_count}: {chapter['title']}",
                message_key="topicBundleRunning",
                message_params={"title": chapter["title"]},
                index=index + 1,
                total=len(run.chapters),
                detail={
                    "chapter_id": topic_key,
                    "chapter_title": chapter["title"],
                    "mode": "sectional",
                    "section_index": section_index,
                    "section_count": section_count,
                },
            )
        )

    theory_step = await _expand_one_theory_chapter(
        run.client,
        run.target,
        body=run.body,
        compact=run.harness.compact,
        chapter=chapter,
        chapters=run.chapters,
        outcomes=run.outcomes,
        book_spine=run.book_spine,
        index=index,
        max_continues=run.harness.theory_max_continues,
        sectional=run.harness.sectional_theory,
        sentences_per_window=run.harness.theory_sentences_per_window,
        prior_chapter_digest="\n".join(prior_digests[-3:]),
        on_section=on_section if run.harness.sectional_theory else None,
    )
    for event in section_events:
        yield event
    if theory_step and run.harness.theory_quality_rounds > 0:
        yield _stage_event(
            stage="theory",
            status="running",
            progress=_band_progress(run.band, index, len(run.chapters)),
            message=f"Quality reinforce: {chapter['title']}",
            message_key="theoryQuality",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=len(run.chapters),
            detail={
                "chapter_id": topic_key,
                "mode": "quality",
                "rounds": run.harness.theory_quality_rounds,
            },
        )
        theory_step, notes = await reinforce_theory_chapter(
            run.client,
            run.target,
            body=run.body,
            chapter=chapter,
            step=theory_step,
            outcomes=run.outcomes,
            max_rounds=run.harness.theory_quality_rounds,
            compact=run.harness.compact,
        )
        run.warnings.extend(notes)
    if not theory_step:
        return
    theory_step["chapter_id"] = topic_key
    parts.theory = split_long_theory_steps(
        [theory_step],
        enabled=run.harness.split_long_theory and run.body.split_long_theory,
        max_parts=3,
    )
    digest = theory_chapter_digest(str(theory_step.get("content") or ""))
    if digest:
        prior_digests.append(digest)


async def _generate_topic_practice(
    run: TopicBundleRun,
    *,
    chapter: dict[str, str],
    topic_key: str,
    per_quiz: int,
    per_practice: int,
    parts: TopicParts,
) -> None:
    if run.body.include_quizzes and per_quiz > 0:
        topic_body = run.body.model_copy(update={"quiz_count": per_quiz})
        parts.quizzes = await generate_quizzes(
            run.client,
            run.target,
            body=topic_body,
            compact=run.harness.compact,
            chapters=[{**chapter, "id": topic_key}],
            outcomes=run.outcomes,
            theory_steps=parts.theory,
            exercise_seeds=run.exercise_seeds,
            fail_soft=run.harness.quiz_fail_soft,
            max_attempts=run.harness.max_quiz_attempts,
            max_tokens=run.harness.quiz_max_tokens,
            warnings=run.warnings,
            quality_rounds=run.harness.quiz_quality_rounds,
        )
        for quiz in parts.quizzes:
            quiz["chapter_id"] = topic_key
            _namespace_step_id(quiz, topic_key)
    if run.use_code and per_practice > 0:
        topic_body = run.body.model_copy(update={"code_count": per_practice})
        parts.codes = await generate_code_tasks(
            run.client,
            run.target,
            body=topic_body,
            compact=run.harness.compact,
            chapters=[{**chapter, "id": topic_key}],
            outcomes=run.outcomes,
            exercise_seeds=run.exercise_seeds,
            quality_rounds=run.harness.practice_quality_rounds,
            fail_soft=run.harness.code_fail_soft,
            warnings=run.warnings,
            theory_steps=parts.theory,
        )
    elif run.use_open and run.body.include_code and per_practice > 0:
        topic_body = run.body.model_copy(update={"code_count": per_practice})
        parts.codes = await generate_open_tasks(
            run.client,
            run.target,
            body=topic_body,
            compact=run.harness.compact,
            chapters=[{**chapter, "id": topic_key}],
            outcomes=run.outcomes,
            domain=run.domain,
            quality_rounds=run.harness.practice_quality_rounds,
            warnings=run.warnings,
            theory_steps=parts.theory,
        )
    for code in parts.codes:
        code["chapter_id"] = topic_key
        _namespace_step_id(code, topic_key)


def _finish_topic(
    run: TopicBundleRun,
    *,
    chapter: dict[str, str],
    chapter_id: str,
    index: int,
    parts: TopicParts,
    saved_ids: set[str],
    per_quiz: int,
    per_practice: int,
) -> bool:
    _ensure_distinct_titles(
        [*parts.theory, *parts.quizzes, *parts.codes],
        fallback_keys=("question", "content"),
    )
    run.result.theory_steps.extend(parts.theory)
    run.result.quiz_steps.extend(parts.quizzes)
    run.result.code_steps.extend(parts.codes)
    is_complete = topic_bundle_complete(
        run.body,
        theory_steps=parts.theory,
        quizzes=parts.quizzes,
        codes=parts.codes,
        quiz_fail_soft=run.harness.quiz_fail_soft,
        expect_quizzes=run.body.include_quizzes and per_quiz > 0,
        expect_codes=run.body.include_code and per_practice > 0,
    )
    if run.store is None or run.user_id is None or run.build_id is None or not is_complete:
        return is_complete
    run.store.save_topic(
        run.user_id,
        run.build_id,
        chapter_id,
        theories=parts.theory,
        quizzes=parts.quizzes,
        codes=parts.codes,
    )
    saved_ids.add(chapter_id)
    run.store.patch_meta(
        run.user_id,
        run.build_id,
        stage="topic_bundle",
        chapters_done=len(saved_ids),
        chapter_total=len(run.chapters),
        progress=_band_progress(run.band, index + 1, len(run.chapters)),
        message=f"Topic bundle ready: {chapter['title']}",
        clear_error=True,
    )
    return is_complete


async def _iter_one_topic(
    run: TopicBundleRun,
    *,
    chapter: dict[str, str],
    topic_key: str,
    index: int,
    saved_ids: set[str],
    prior_digests: list[str],
) -> AsyncIterator[dict[str, object]]:
    restored = _restore_topic(run, chapter_id=topic_key, saved_ids=saved_ids)
    if restored is not None:
        for step in restored.theory:
            digest = theory_chapter_digest(str(step.get("content") or ""))
            if digest:
                prior_digests.append(digest)
        yield _stage_event(
            stage="topic_bundle",
            status="done",
            progress=_band_progress(run.band, index + 1, len(run.chapters)),
            message=f"Topic bundle restored: {chapter['title']}",
            message_key="topicBundleRestored",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=len(run.chapters),
            detail={"chapter_id": topic_key, "restored": True},
        )
        return
    yield _stage_event(
        stage="topic_bundle",
        status="running",
        progress=_band_progress(run.band, index, len(run.chapters)),
        message=f"Building topic bundle: {chapter['title']}",
        message_key="topicBundleRunning",
        message_params={"title": chapter["title"]},
        index=index + 1,
        total=len(run.chapters),
        detail={"chapter_id": topic_key, "chapter_title": chapter["title"]},
    )
    parts = TopicParts()
    async for event in _iter_topic_theory(
        run,
        chapter=chapter,
        topic_key=topic_key,
        index=index,
        prior_digests=prior_digests,
        parts=parts,
    ):
        yield event
    per_quiz, per_practice = _per_topic_counts(
        run.body,
        topic_total=len(run.chapters),
        topic_index=index,
    )
    await _generate_topic_practice(
        run,
        chapter=chapter,
        topic_key=topic_key,
        per_quiz=per_quiz,
        per_practice=per_practice,
        parts=parts,
    )
    is_complete = _finish_topic(
        run,
        chapter=chapter,
        chapter_id=topic_key,
        index=index,
        parts=parts,
        saved_ids=saved_ids,
        per_quiz=per_quiz,
        per_practice=per_practice,
    )
    yield _stage_event(
        stage="topic_bundle",
        status="done",
        progress=_band_progress(run.band, index + 1, len(run.chapters)),
        message=f"Topic bundle ready: {chapter['title']}",
        message_key="topicBundleDone",
        message_params={"title": chapter["title"]},
        index=index + 1,
        total=len(run.chapters),
        detail={
            "chapter_id": topic_key,
            "theory": len(parts.theory),
            "quizzes": per_quiz if run.body.include_quizzes else 0,
            "practice": per_practice if run.body.include_code else 0,
            "checkpoint_saved": is_complete,
        },
    )


async def iter_topic_bundle_stages(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    domain: str,
    use_code: bool,
    use_open: bool,
    band: tuple[float, float],
    warnings: list[str],
    result: TopicBundleResult,
    store: CourseBuildStore | None = None,
    user_id: uuid.UUID | None = None,
    build_id: uuid.UUID | None = None,
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> AsyncIterator[dict[str, object]]:
    if not chapters:
        return
    run = TopicBundleRun(
        client=client,
        target=target,
        body=body,
        harness=harness,
        chapters=chapters,
        outcomes=outcomes,
        book_spine=book_spine,
        domain=domain,
        use_code=use_code,
        use_open=use_open,
        band=band,
        warnings=warnings,
        result=result,
        store=store,
        user_id=user_id,
        build_id=build_id,
        exercise_seeds=exercise_seeds,
    )
    saved_ids = (
        store.list_topic_ids(user_id, build_id)
        if store is not None and user_id is not None and build_id is not None
        else set()
    )
    prior_digests: list[str] = []
    topic_keys = _topic_keys(chapters)
    for index, chapter in enumerate(chapters):
        async for event in _iter_one_topic(
            run,
            chapter=chapter,
            topic_key=topic_keys[index],
            index=index,
            saved_ids=saved_ids,
            prior_digests=prior_digests,
        ):
            yield event
