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
from .source_exercise_harvest import HarvestedExercise
from .stage_llm import _stage_json

_MAX_PRACTICE = 12
_CODE_REPAIR_HINT = (
    "\n\n## Repair\n"
    "Previous JSON was invalid for a code task. Return exactly one object under "
    '"tasks" (or "task") with non-empty string fields: id, title, content, '
    "template (starter source code), and tests as a non-empty array of "
    '{ "input": [...], "output": ... } or { "run": "..." }. '
    'If you cannot invent executable tests, set "checker": "llm" and a short '
    '"rubric", keep "template" non-empty, and use "tests": [].'
)


def _ladder_levels(count: int) -> list[str]:
    """Лёгкие → нормальные → сложные по кругу до count (макс. 12)."""
    n = max(0, min(count, _MAX_PRACTICE))
    order = ("easy", "medium", "hard")
    return [order[i % 3] for i in range(n)]


def _coerce_tasks_payload(payload: dict[str, Any]) -> list[object]:
    tasks = payload.get("tasks")
    if isinstance(tasks, list):
        return tasks
    task = payload.get("task")
    if isinstance(task, dict):
        return [task]
    if any(
        payload.get(key)
        for key in ("template", "code", "starter_code", "starter", "solution_template")
    ) or payload.get("kind") in {"code", "task"}:
        return [payload]
    return []


def _compact_code_scaffold(
    *,
    level: str,
    index: int,
    runtime: str,
    runtime_version: str,
    chapters: list[dict[str, str]],
    outcomes: list[str],
) -> dict[str, object]:
    topic = "the article"
    if chapters:
        topic = str(chapters[0].get("title") or "").strip() or topic
    if topic == "the article" and outcomes:
        topic = str(outcomes[0]).strip() or topic
    lang = (runtime or "python").strip() or "python"
    version = (runtime_version or "").strip()
    title = f"Practice ({level}): {topic}"[:120]
    content = f"Write a small {lang} snippet that demonstrates: {topic}. Difficulty: {level}."
    if lang.casefold() in {"python", "python3"}:
        template = (
            '"""Starter — replace pass with a working solution."""\n'
            "\n"
            "def solve() -> str:\n"
            "    pass\n"
            "\n"
            'if __name__ == "__main__":\n'
            "    print(solve())\n"
        )
    else:
        template = f"// Starter for {level} practice about {topic}\n"
    return {
        "id": f"code-{level}-{index + 1}",
        "kind": "code",
        "level": level,
        "title": title,
        "content": content,
        "runtime": lang,
        "runtime_version": version,
        "template": template,
        "tests": [],
        "checker": "llm",
        "rubric": content[:500],
    }


async def _fetch_normalized_code_task(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    level: str,
    index: int,
    prior_titles: list[str],
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> dict[str, object] | None:
    base_message = _code_one_task_user_message(
        body,
        outcomes=outcomes,
        chapters=chapters,
        level=level,
        index=index,
        prior_titles=prior_titles,
        exercise_seeds=exercise_seeds,
    )
    attempts = (base_message, base_message + _CODE_REPAIR_HINT)
    for attempt, user_message in enumerate(attempts):
        payload = await _stage_json(
            client,
            target,
            compact=compact,
            stage="code",
            user_message=user_message,
            max_tokens=(3200 if attempt else 2800) if compact else 5200,
        )
        batch = _normalize_code_tasks(
            _coerce_tasks_payload(payload),
            count=1,
            runtime=(body.runtime or "python"),
            runtime_version=(body.runtime_version or ""),
        )
        if batch:
            task = dict(batch[0])
            task["level"] = level
            return task
    return None


async def generate_code_tasks(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    for index, level in enumerate(_ladder_levels(body.code_count)):
        prior_titles = [str(item.get("title") or "") for item in collected]
        task = await _fetch_normalized_code_task(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            level=level,
            index=index,
            prior_titles=prior_titles,
            exercise_seeds=exercise_seeds,
        )
        if task is None and compact:
            # Local models often return JSON that fails strict normalize; keep build alive.
            task = _compact_code_scaffold(
                level=level,
                index=index,
                runtime=(body.runtime or "python"),
                runtime_version=(body.runtime_version or ""),
                chapters=chapters,
                outcomes=outcomes,
            )
        if task is None:
            raise TutorError(
                status.HTTP_502_BAD_GATEWAY,
                f"course code stage returned no task for level={level}",
            )
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
