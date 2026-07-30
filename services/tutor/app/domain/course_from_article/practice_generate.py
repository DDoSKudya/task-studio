from __future__ import annotations

from typing import Any

import httpx
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .messages import (
    _code_one_task_user_message,
    _task_one_user_message,
)
from .normalize import _normalize_code_tasks, _normalize_open_tasks
from .stage_llm import _stage_json

_LEVELS = ("easy", "medium", "hard", "expert", "capstone")


def _ladder_levels(count: int) -> list[str]:
    n = max(1, min(int(count), len(_LEVELS)))
    return list(_LEVELS[:n])


def _coerce_tasks_payload(payload: dict[str, Any]) -> list[object]:
    tasks = payload.get("tasks")
    if isinstance(tasks, list):
        return tasks
    task = payload.get("task")
    if isinstance(task, dict):
        return [task]
    if payload.get("template") or payload.get("kind") in {"code", "task"}:
        return [payload]
    return []


async def generate_code_tasks(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
) -> list[dict[str, object]]:

    collected: list[dict[str, object]] = []
    for index, level in enumerate(_ladder_levels(body.code_count)):
        prior_titles = [str(item.get("title") or "") for item in collected]
        payload = await _stage_json(
            client,
            target,
            compact=compact,
            stage="code",
            user_message=_code_one_task_user_message(
                body,
                outcomes=outcomes,
                chapters=chapters,
                level=level,
                index=index,
                prior_titles=prior_titles,
            ),
            max_tokens=2800 if compact else 5200,
        )
        batch = _normalize_code_tasks(
            _coerce_tasks_payload(payload),
            count=1,
            runtime=body.runtime,
            runtime_version=body.runtime_version,
        )
        if not batch:
            raise TutorError(
                status.HTTP_502_BAD_GATEWAY,
                f"course code stage returned no task for level={level}",
            )
        task = dict(batch[0])
        task["level"] = level
        collected.append(task)
    if len(collected) < min(3, body.code_count):
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course code stage returned too few tasks")
    return collected


async def generate_open_tasks(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    domain: str,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    for index, level in enumerate(_ladder_levels(body.code_count)):
        prior_titles = [str(item.get("title") or "") for item in collected]
        payload = await _stage_json(
            client,
            target,
            compact=compact,
            stage="tasks",
            user_message=_task_one_user_message(
                body,
                outcomes=outcomes,
                chapters=chapters,
                domain=domain,
                level=level,
                index=index,
                prior_titles=prior_titles,
            ),
            max_tokens=2200 if compact else 4200,
        )
        batch = _normalize_open_tasks(_coerce_tasks_payload(payload), count=1)
        if not batch:
            raise TutorError(
                status.HTTP_502_BAD_GATEWAY,
                f"course task stage returned no task for level={level}",
            )
        task = dict(batch[0])
        collected.append(task)
    if len(collected) < min(3, body.code_count):
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course task stage returned too few tasks")
    return collected
