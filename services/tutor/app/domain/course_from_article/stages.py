from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .practice_generate import generate_code_tasks, generate_open_tasks
from .progress import _stage_event
from .quiz_generate import generate_quizzes
from .stages_parallel import _iter_quizzes_and_code_parallel, _tests_count

__all__ = [
    "_iter_code_stage",
    "_iter_practice_stage",
    "_iter_quizzes_and_code_parallel",
    "_iter_quizzes_stage",
    "_iter_task_stage",
]


async def _iter_quizzes_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    band_quizzes: tuple[float, float],
    quiz_steps_out: list[dict[str, object]],
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
        compact=compact,
        chapters=chapters,
        outcomes=outcomes,
        theory_steps=theory_steps,
    )
    if len(quiz_steps) < 3:
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
) -> AsyncIterator[dict[str, object]]:
    if domain in {"language", "general"}:
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
    ):
        yield event


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
) -> AsyncIterator[dict[str, object]]:
    yield _stage_event(
        stage="tasks",
        status="running",
        progress=band_code[0],
        message=f"Building {body.code_count}-step open-task ladder",
        message_key="codeBuilding",
        message_params={"count": body.code_count},
        detail={"task_count": body.code_count, "domain": domain},
    )
    payload = await generate_open_tasks(
        client,
        target,
        body=body,
        compact=compact,
        chapters=chapters,
        outcomes=outcomes,
        domain=domain,
    )
    steps = payload
    if len(steps) < 3:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course task stage returned too few tasks")
    code_steps_out.extend(steps)
    yield _stage_event(
        stage="tasks",
        status="done",
        progress=band_code[1],
        message=f"Prepared {len(steps)} open tasks",
        message_key="codePrepared",
        message_params={"count": len(steps)},
        detail={
            "task_count": len(steps),
            "domain": domain,
            "tasks": [{"id": t.get("id"), "title": t.get("title")} for t in steps],
        },
    )


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
    )
    if len(code_steps) < 3:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course code stage returned too few tasks")
    code_steps_out.extend(code_steps)
    yield _stage_event(
        stage="code",
        status="done",
        progress=band_code[1],
        message=f"Prepared {len(code_steps)} code tasks",
        message_key="codePrepared",
        message_params={"count": len(code_steps)},
        detail={
            "task_count": len(code_steps),
            "tasks": [
                {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "tests": _tests_count(task),
                }
                for task in code_steps
            ],
        },
    )
