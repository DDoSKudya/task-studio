from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from app.domain.course_from_article.common.runtime.provider_policy import CourseHarnessPolicy
from app.domain.course_from_article.practice.practice_generate import (
    generate_code_tasks,
    generate_open_tasks,
)
from app.domain.course_from_article.practice.quiz_generate import generate_quizzes
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_from_article.workflow.events.progress import _stage_event
from app.domain.course_from_article.workflow.stages.stages_parallel import (
    _iter_quizzes_and_code_parallel,
    _tests_count,
)
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

__all__ = [
    "_iter_practice_stage",
    "_iter_quizzes_and_code_parallel",
    "_iter_quizzes_stage",
]


async def _iter_quizzes_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    band_quizzes: tuple[float, float],
    quiz_steps_out: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None = None,
    warnings: list[str] | None = None,
) -> AsyncIterator[dict[str, object]]:
    yield _stage_event(
        stage="quizzes",
        status="running",
        progress=band_quizzes[0],
        message=f"Designing {body.quiz_count} knowledge-check quizzes",
        message_key="quizzesDesigning",
        message_params={"count": body.quiz_count},
        detail={"quiz_count": body.quiz_count},
    )
    quiz_steps = await generate_quizzes(
        client,
        target,
        body=body,
        compact=harness.compact,
        chapters=chapters,
        outcomes=outcomes,
        theory_steps=theory_steps,
        exercise_seeds=exercise_seeds,
        fail_soft=harness.quiz_fail_soft,
        max_attempts=harness.max_quiz_attempts,
        max_tokens=harness.quiz_max_tokens,
        warnings=warnings,
        quality_rounds=harness.quiz_quality_rounds,
    )
    min_quizzes = 0 if harness.quiz_fail_soft else 3
    if len(quiz_steps) < min_quizzes:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course quizzes stage returned too few items")
    quiz_steps_out.extend(quiz_steps)
    yield _stage_event(
        stage="quizzes",
        status="done",
        progress=band_quizzes[1],
        message=f"Prepared {len(quiz_steps)} quizzes",
        message_key="quizzesPrepared",
        message_params={"count": len(quiz_steps)},
        detail={
            "quiz_count": len(quiz_steps),
            "quizzes": [
                {"id": q.get("id"), "title": q.get("title"), "question": q.get("question")}
                for q in quiz_steps
            ],
        },
    )


async def _iter_practice_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    band_code: tuple[float, float],
    code_steps_out: list[dict[str, object]],
    domain: str,
    prefer_open: bool = False,
    exercise_seeds: list[HarvestedExercise] | None = None,
    quality_rounds: int = 0,
    code_fail_soft: bool = False,
    warnings: list[str] | None = None,
    theory_steps: list[dict[str, object]] | None = None,
) -> AsyncIterator[dict[str, object]]:
    if prefer_open or domain in {"language", "general"}:
        async for event in _iter_task_stage(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            band_code=band_code,
            code_steps_out=code_steps_out,
            domain=domain,
            quality_rounds=quality_rounds,
            warnings=warnings,
            theory_steps=theory_steps,
        ):
            yield event
        return
    async for event in _iter_code_stage(
        client,
        target,
        body=body,
        compact=compact,
        chapters=chapters,
        outcomes=outcomes,
        band_code=band_code,
        code_steps_out=code_steps_out,
        exercise_seeds=exercise_seeds,
        quality_rounds=quality_rounds,
        code_fail_soft=code_fail_soft,
        warnings=warnings,
        theory_steps=theory_steps,
    ):
        yield event


async def _iter_code_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    band_code: tuple[float, float],
    code_steps_out: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None = None,
    quality_rounds: int = 0,
    code_fail_soft: bool = False,
    warnings: list[str] | None = None,
    theory_steps: list[dict[str, object]] | None = None,
) -> AsyncIterator[dict[str, object]]:
    yield _stage_event(
        stage="code",
        status="running",
        progress=band_code[0],
        message=f"Building {body.code_count}-step code ladder (easy→hard)",
        message_key="codeBuilding",
        message_params={"count": body.code_count},
        detail={"code_count": body.code_count, "runtime": body.runtime},
    )
    code_steps = await generate_code_tasks(
        client,
        target,
        body=body,
        compact=compact,
        chapters=chapters,
        outcomes=outcomes,
        exercise_seeds=exercise_seeds,
        quality_rounds=quality_rounds,
        fail_soft=code_fail_soft,
        warnings=warnings,
        theory_steps=theory_steps,
    )
    min_required = 0 if code_fail_soft else min(3, max(0, body.code_count))
    if len(code_steps) < min_required:
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            "course practice stage returned too few tasks",
        )
    code_steps_out.extend(code_steps)
    yield _stage_event(
        stage="code",
        status="done",
        progress=band_code[1],
        message=f"Prepared {len(code_steps)} practice tasks",
        message_key="codePrepared",
        message_params={"count": len(code_steps)},
        detail={
            "task_count": len(code_steps),
            "tasks": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "tests": _tests_count(item),
                }
                for item in code_steps
            ],
        },
    )


async def _iter_task_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    band_code: tuple[float, float],
    code_steps_out: list[dict[str, object]],
    domain: str,
    quality_rounds: int = 0,
    warnings: list[str] | None = None,
    theory_steps: list[dict[str, object]] | None = None,
) -> AsyncIterator[dict[str, object]]:
    yield _stage_event(
        stage="tasks",
        status="running",
        progress=band_code[0],
        message=f"Building {body.code_count}-step open-task ladder",
        message_key="codeBuilding",
        message_params={"count": body.code_count},
        detail={"code_count": body.code_count, "domain": domain},
    )
    code_steps = await generate_open_tasks(
        client,
        target,
        body=body,
        compact=compact,
        chapters=chapters,
        outcomes=outcomes,
        domain=domain,
        quality_rounds=quality_rounds,
        warnings=warnings,
        theory_steps=theory_steps,
    )
    if len(code_steps) < 1:
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            "course practice stage returned too few tasks",
        )
    code_steps_out.extend(code_steps)
    yield _stage_event(
        stage="tasks",
        status="done",
        progress=band_code[1],
        message=f"Prepared {len(code_steps)} practice tasks",
        message_key="codePrepared",
        message_params={"count": len(code_steps)},
        detail={
            "task_count": len(code_steps),
            "domain": domain,
            "tasks": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "kind": item.get("kind"),
                }
                for item in code_steps
            ],
        },
    )
