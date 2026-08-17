from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.common.runtime.provider_policy import CourseHarnessPolicy
from app.domain.course_from_article.curriculum.theory.theory import _iter_theory_expansion
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_from_article.quality.polish import _iter_book_polish
from app.domain.course_from_article.workflow.events.progress import _stage_event
from app.domain.course_from_article.workflow.stages.stages import (
    _iter_practice_stage,
    _iter_quizzes_and_code_parallel,
    _iter_quizzes_stage,
)
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


@dataclass
class ContentStageResult:
    theory_steps: list[dict[str, object]] = field(default_factory=list)
    quiz_steps: list[dict[str, object]] = field(default_factory=list)
    code_steps: list[dict[str, object]] = field(default_factory=list)


async def _iter_theory_content(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    band_theory: tuple[float, float],
    band_polish: tuple[float, float],
    theory_steps: list[dict[str, object]],
    warnings: list[str],
    store: CourseBuildStore | None,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
) -> AsyncIterator[dict[str, object]]:
    async for event in _iter_theory_expansion(
        client,
        target,
        body=body,
        compact=harness.compact,
        chapters=chapters,
        outcomes=outcomes,
        book_spine=book_spine,
        band_theory=band_theory,
        theory_steps=theory_steps,
        store=store,
        user_id=user_id,
        build_id=build_id,
        sectional=harness.sectional_theory,
        max_continues=harness.theory_max_continues,
        sentences_per_window=harness.theory_sentences_per_window,
        quality_rounds=harness.theory_quality_rounds,
        warnings=warnings,
    ):
        yield event

    if len(theory_steps) >= 1 and harness.run_polish:
        async for event in _iter_book_polish(
            client,
            target,
            body=body,
            compact=harness.compact,
            chapters=chapters,
            book_spine=book_spine,
            band_polish=band_polish,
            theory_steps=theory_steps,
        ):
            yield event
    elif theory_steps:
        yield _stage_event(
            stage="polish",
            status="done",
            progress=band_polish[1],
            message="Book polish applied to 0 chapter(s)",
            message_key="polishDone",
            message_params={"count": 0},
            detail={
                "edits_applied": 0,
                "chapter_count": len(theory_steps),
                "skipped": True,
            },
        )


def _load_restored_content(
    store: CourseBuildStore | None,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
) -> tuple[list[dict[str, object]] | None, list[dict[str, object]] | None]:
    if store is None or user_id is None or build_id is None:
        return None, None
    return store.load_quizzes(user_id, build_id), store.load_codes(user_id, build_id)


def _save_content(
    store: CourseBuildStore | None,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
    *,
    quizzes: list[dict[str, object]] | None = None,
    codes: list[dict[str, object]] | None = None,
) -> None:
    if store is None or user_id is None or build_id is None:
        return
    if quizzes is not None:
        store.save_quizzes(user_id, build_id, quizzes)
    if codes is not None:
        store.save_codes(user_id, build_id, codes)


async def _iter_restored_content(
    body: CourseFromArticleRequest,
    *,
    restored_quizzes: list[dict[str, object]] | None,
    restored_codes: list[dict[str, object]] | None,
    quiz_steps: list[dict[str, object]],
    code_steps: list[dict[str, object]],
    band_quizzes: tuple[float, float],
    band_code: tuple[float, float],
) -> AsyncIterator[dict[str, object]]:
    if body.include_quizzes and restored_quizzes:
        quiz_steps.extend(restored_quizzes)
        yield _stage_event(
            stage="quizzes",
            status="done",
            progress=band_quizzes[1],
            message=f"Quizzes restored ({len(restored_quizzes)})",
            message_key="quizzesRestored",
            message_params={"count": len(restored_quizzes)},
            detail={"restored": True, "count": len(restored_quizzes)},
        )
    if body.include_code and restored_codes:
        code_steps.extend(restored_codes)
        yield _stage_event(
            stage="code",
            status="done",
            progress=band_code[1],
            message=f"Practice restored ({len(restored_codes)})",
            message_key="codeRestored",
            message_params={"count": len(restored_codes)},
            detail={"restored": True, "count": len(restored_codes)},
        )


async def _iter_code_content(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    band_code: tuple[float, float],
    code_steps: list[dict[str, object]],
    domain: str,
    use_code: bool,
    use_open: bool,
    exercise_seeds: list[HarvestedExercise] | None,
    warnings: list[str],
    theory_steps: list[dict[str, object]],
) -> AsyncIterator[dict[str, object]]:
    async for event in _iter_practice_stage(
        client,
        target,
        body=body,
        compact=harness.compact,
        chapters=chapters,
        outcomes=outcomes,
        band_code=band_code,
        code_steps_out=code_steps,
        domain=domain,
        prefer_open=use_open and not use_code,
        exercise_seeds=exercise_seeds,
        quality_rounds=harness.practice_quality_rounds,
        code_fail_soft=harness.code_fail_soft,
        warnings=warnings,
        theory_steps=theory_steps,
    ):
        yield event


async def _iter_parallel_content(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    domain: str,
    band_quizzes: tuple[float, float],
    band_code: tuple[float, float],
    theory_steps: list[dict[str, object]],
    quiz_steps: list[dict[str, object]],
    code_steps: list[dict[str, object]],
    practice_is_open: bool,
    exercise_seeds: list[HarvestedExercise] | None,
    warnings: list[str],
) -> AsyncIterator[dict[str, object]]:
    async for event in _iter_quizzes_and_code_parallel(
        client,
        target,
        body=body,
        harness=harness,
        chapters=chapters,
        outcomes=outcomes,
        theory_steps=theory_steps,
        band_quizzes=band_quizzes,
        band_code=band_code,
        quiz_steps_out=quiz_steps,
        code_steps_out=code_steps,
        domain=domain,
        practice_is_open=practice_is_open,
        exercise_seeds=exercise_seeds,
        warnings=warnings,
    ):
        yield event


async def _iter_serial_content(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    domain: str,
    band_quizzes: tuple[float, float],
    band_code: tuple[float, float],
    theory_steps: list[dict[str, object]],
    quiz_steps: list[dict[str, object]],
    code_steps: list[dict[str, object]],
    need_quizzes: bool,
    need_code: bool,
    use_code: bool,
    use_open: bool,
    exercise_seeds: list[HarvestedExercise] | None,
    warnings: list[str],
    store: CourseBuildStore | None,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
) -> AsyncIterator[dict[str, object]]:
    if need_quizzes:
        async for event in _iter_quizzes_stage(
            client,
            target,
            body=body,
            harness=harness,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            band_quizzes=band_quizzes,
            quiz_steps_out=quiz_steps,
            exercise_seeds=exercise_seeds,
            warnings=warnings,
        ):
            yield event
        _save_content(store, user_id, build_id, quizzes=quiz_steps)

    if need_code:
        async for event in _iter_code_content(
            client,
            target,
            body=body,
            harness=harness,
            chapters=chapters,
            outcomes=outcomes,
            band_code=band_code,
            code_steps=code_steps,
            domain=domain,
            use_code=use_code,
            use_open=use_open,
            exercise_seeds=exercise_seeds,
            warnings=warnings,
            theory_steps=theory_steps,
        ):
            yield event
        _save_content(store, user_id, build_id, codes=code_steps)


async def iter_content_stages(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    domain: str,
    band_theory: tuple[float, float],
    band_polish: tuple[float, float],
    band_quizzes: tuple[float, float],
    band_code: tuple[float, float],
    warnings: list[str],
    result: ContentStageResult,
    use_code: bool = True,
    use_open: bool = False,
    practice_is_open: bool = False,
    store: CourseBuildStore | None = None,
    user_id: uuid.UUID | None = None,
    build_id: uuid.UUID | None = None,
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> AsyncIterator[dict[str, object]]:
    if body.include_theory:
        async for event in _iter_theory_content(
            client,
            target,
            body=body,
            harness=harness,
            chapters=chapters,
            outcomes=outcomes,
            book_spine=book_spine,
            band_theory=band_theory,
            band_polish=band_polish,
            theory_steps=result.theory_steps,
            warnings=warnings,
            store=store,
            user_id=user_id,
            build_id=build_id,
        ):
            yield event

    restored_quizzes, restored_codes = _load_restored_content(store, user_id, build_id)
    async for event in _iter_restored_content(
        body,
        restored_quizzes=restored_quizzes,
        restored_codes=restored_codes,
        quiz_steps=result.quiz_steps,
        code_steps=result.code_steps,
        band_quizzes=band_quizzes,
        band_code=band_code,
    ):
        yield event
    need_quizzes = body.include_quizzes and not restored_quizzes
    need_code = body.include_code and not restored_codes
    if need_quizzes and need_code and not harness.compact:
        async for event in _iter_parallel_content(
            client,
            target,
            body=body,
            harness=harness,
            chapters=chapters,
            outcomes=outcomes,
            domain=domain,
            band_quizzes=band_quizzes,
            band_code=band_code,
            theory_steps=result.theory_steps,
            quiz_steps=result.quiz_steps,
            code_steps=result.code_steps,
            practice_is_open=practice_is_open or (use_open and not use_code),
            exercise_seeds=exercise_seeds,
            warnings=warnings,
        ):
            yield event
        _save_content(
            store,
            user_id,
            build_id,
            quizzes=result.quiz_steps,
            codes=result.code_steps,
        )
        return
    async for event in _iter_serial_content(
        client,
        target,
        body=body,
        harness=harness,
        chapters=chapters,
        outcomes=outcomes,
        domain=domain,
        band_quizzes=band_quizzes,
        band_code=band_code,
        theory_steps=result.theory_steps,
        quiz_steps=result.quiz_steps,
        code_steps=result.code_steps,
        need_quizzes=need_quizzes,
        need_code=need_code,
        use_code=use_code,
        use_open=use_open,
        exercise_seeds=exercise_seeds,
        warnings=warnings,
        store=store,
        user_id=user_id,
        build_id=build_id,
    ):
        yield event
