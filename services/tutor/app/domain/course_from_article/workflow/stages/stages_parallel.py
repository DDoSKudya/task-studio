from __future__ import annotations

import asyncio
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
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


def _tests_count(task: dict[str, object]) -> int:
    tests = task.get("tests")
    return len(tests) if isinstance(tests, list) else 0


async def _generate_parallel_quizzes(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None,
    warnings: list[str] | None,
) -> list[dict[str, object]]:
    steps = await generate_quizzes(
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
    if len(steps) < min_quizzes:
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            "course quizzes stage returned too few items",
        )
    return steps


async def _generate_parallel_practice(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    domain: str,
    practice_is_open: bool,
    exercise_seeds: list[HarvestedExercise] | None,
    warnings: list[str] | None,
) -> list[dict[str, object]]:
    if practice_is_open:
        steps = await generate_open_tasks(
            client,
            target,
            body=body,
            compact=harness.compact,
            chapters=chapters,
            outcomes=outcomes,
            domain=domain,
            quality_rounds=harness.practice_quality_rounds,
            warnings=warnings,
            theory_steps=theory_steps,
        )
    else:
        steps = await generate_code_tasks(
            client,
            target,
            body=body,
            compact=harness.compact,
            chapters=chapters,
            outcomes=outcomes,
            exercise_seeds=exercise_seeds,
            quality_rounds=harness.practice_quality_rounds,
            fail_soft=harness.code_fail_soft,
            warnings=warnings,
            theory_steps=theory_steps,
        )
    min_practice = (
        0
        if harness.code_fail_soft
        else (1 if practice_is_open else min(3, max(0, body.code_count)))
    )
    if body.code_count > 0 and len(steps) < min_practice:
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            "course practice stage returned too few tasks",
        )
    return steps


async def _iter_quizzes_and_code_parallel(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    harness: CourseHarnessPolicy,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    band_quizzes: tuple[float, float],
    band_code: tuple[float, float],
    quiz_steps_out: list[dict[str, object]],
    code_steps_out: list[dict[str, object]],
    domain: str = "code",
    practice_is_open: bool = False,
    exercise_seeds: list[HarvestedExercise] | None = None,
    warnings: list[str] | None = None,
) -> AsyncIterator[dict[str, object]]:
    practice_is_open = practice_is_open or domain in {"language", "general"}
    practice_stage = "tasks" if practice_is_open else "code"
    yield _stage_event(
        stage="quizzes",
        status="running",
        progress=band_quizzes[0],
        message=f"Designing {body.quiz_count} knowledge-check quizzes",
        message_key="quizzesDesigning",
        message_params={"count": body.quiz_count},
        detail={"quiz_count": body.quiz_count, "mode": "parallel"},
    )
    yield _stage_event(
        stage=practice_stage,
        status="running",
        progress=band_code[0],
        message=(
            f"Building {body.code_count}-step open-task ladder"
            if practice_is_open
            else f"Building {body.code_count}-step code ladder (easy→hard)"
        ),
        message_key="codeBuilding",
        message_params={"count": body.code_count},
        detail={
            "code_count": body.code_count,
            "runtime": body.runtime,
            "domain": domain,
            "mode": "parallel",
        },
    )

    quiz_steps, practice_steps = await asyncio.gather(
        _generate_parallel_quizzes(
            client,
            target,
            body=body,
            harness=harness,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            exercise_seeds=exercise_seeds,
            warnings=warnings,
        ),
        _generate_parallel_practice(
            client,
            target,
            body=body,
            harness=harness,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            domain=domain,
            practice_is_open=practice_is_open,
            exercise_seeds=exercise_seeds,
            warnings=warnings,
        ),
    )
    quiz_steps_out.extend(quiz_steps)
    code_steps_out.extend(practice_steps)

    yield _stage_event(
        stage="quizzes",
        status="done",
        progress=band_quizzes[1],
        message=f"Prepared {len(quiz_steps)} quizzes",
        message_key="quizzesPrepared",
        message_params={"count": len(quiz_steps)},
        detail={
            "quiz_count": len(quiz_steps),
            "mode": "parallel",
            "quizzes": [
                {"id": q.get("id"), "title": q.get("title"), "question": q.get("question")}
                for q in quiz_steps
            ],
        },
    )
    yield _stage_event(
        stage=practice_stage,
        status="done",
        progress=band_code[1],
        message=f"Prepared {len(practice_steps)} practice tasks",
        message_key="codePrepared",
        message_params={"count": len(practice_steps)},
        detail={
            "task_count": len(practice_steps),
            "mode": "parallel",
            "domain": domain,
            "tasks": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "kind": item.get("kind"),
                    "tests": _tests_count(item),
                }
                for item in practice_steps
            ],
        },
    )
