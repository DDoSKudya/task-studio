from __future__ import annotations

from typing import Any

import httpx
from app.domain.course_from_article.common.content.messages import (
    _code_one_task_user_message,
    _task_one_user_message,
)
from app.domain.course_from_article.common.content.normalize import (
    _normalize_code_tasks,
    _normalize_open_tasks,
)
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_from_article.common.runtime.stage_llm import _stage_json
from app.domain.course_from_article.practice.normalize_practice import _open_task_from_code_shim
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_from_article.quality.assess_quality import reinforce_practice_task
from app.domain.course_strategies.code_templates import code_template_is_substantive
from app.domain.errors import TutorError
from app.domain.llm.transport.retry import should_retry_json_error
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

_MAX_PRACTICE = 12
_OPEN_TASK_ATTEMPTS = 4
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


def _ensure_deliverable_practice(
    task: dict[str, object],
    *,
    notes: list[str],
) -> dict[str, object]:
    template = str(task.get("template") or "")
    if code_template_is_substantive(template):
        return task
    label = str(task.get("title") or task.get("id") or "practice")
    notes.append(f"practice converted to open task after weak code template: {label}")
    return _open_task_from_code_shim(
        task_id=str(task.get("id") or "code-practice"),
        level=str(task.get("level") or "easy"),
        title=label,
        content=str(task.get("content") or ""),
        rubric=str(task.get("rubric") or ""),
        runtime=str(task.get("runtime") or ""),
    )


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
    attempts = (
        base_message,
        base_message + _CODE_REPAIR_HINT,
        base_message,
        base_message + _CODE_REPAIR_HINT,
    )
    for attempt, user_message in enumerate(attempts):
        try:
            payload = await _stage_json(
                client,
                target,
                compact=compact,
                stage="code",
                user_message=user_message,
                max_tokens=(3200 if attempt else 2800)
                if compact
                else COURSE_LLM.code_stage_max_tokens,
            )
        except TutorError as exc:
            if not should_retry_json_error(exc, attempt=attempt, attempts=len(attempts)):
                raise
            continue
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
    quality_rounds: int = 0,
    fail_soft: bool = False,
    warnings: list[str] | None = None,
    theory_steps: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    notes = warnings if warnings is not None else []
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
        if task is None and (compact or fail_soft):
            task = _compact_code_scaffold(
                level=level,
                index=index,
                runtime=(body.runtime or "python"),
                runtime_version=(body.runtime_version or ""),
                chapters=chapters,
                outcomes=outcomes,
            )
            if fail_soft and task is not None:
                notes.append(f"code scaffold fallback for level={level}")
        if task is None:
            raise TutorError(
                status.HTTP_502_BAD_GATEWAY,
                f"course code stage returned no task for level={level}",
            )
        if quality_rounds > 0:
            task, reinforce_notes = await reinforce_practice_task(
                client,
                target,
                body=body,
                task=task,
                chapters=chapters,
                outcomes=outcomes,
                kind="code",
                max_rounds=quality_rounds,
                compact=compact,
                theory_steps=theory_steps,
            )
            notes.extend(reinforce_notes)
        collected.append(_ensure_deliverable_practice(task, notes=notes))
    min_required = 0 if fail_soft else min(3, body.code_count)
    if len(collected) < min_required:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course code stage returned too few tasks")
    return collected


async def _fetch_open_task(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    domain: str,
    level: str,
    index: int,
    prior_titles: list[str],
) -> dict[str, object]:
    for attempt in range(_OPEN_TASK_ATTEMPTS):
        try:
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
                max_tokens=COURSE_LLM.practice_max_tokens
                if compact
                else COURSE_LLM.practice_stage_max_tokens,
            )
        except TutorError as exc:
            if not should_retry_json_error(exc, attempt=attempt, attempts=_OPEN_TASK_ATTEMPTS):
                raise
            continue
        if batch := _normalize_open_tasks(_coerce_tasks_payload(payload), count=1):
            return dict(batch[0])
    raise TutorError(
        status.HTTP_502_BAD_GATEWAY,
        f"course task stage returned no task for level={level}",
    )


async def generate_open_tasks(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    domain: str,
    quality_rounds: int = 0,
    warnings: list[str] | None = None,
    theory_steps: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    notes = warnings if warnings is not None else []
    for index, level in enumerate(_ladder_levels(body.code_count)):
        prior_titles = [str(item.get("title") or "") for item in collected]
        task = await _fetch_open_task(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            domain=domain,
            level=level,
            index=index,
            prior_titles=prior_titles,
        )
        if quality_rounds > 0:
            task, reinforce_notes = await reinforce_practice_task(
                client,
                target,
                body=body,
                task=task,
                chapters=chapters,
                outcomes=outcomes,
                kind="open",
                max_rounds=quality_rounds,
                compact=compact,
                theory_steps=theory_steps,
            )
            notes.extend(reinforce_notes)
        collected.append(task)
    if len(collected) < min(3, body.code_count):
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course task stage returned too few tasks")
    return collected
