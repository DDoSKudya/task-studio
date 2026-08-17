from __future__ import annotations

import re

from app.domain.course_from_article.common.content.textutil import _as_str, _slug
from app.domain.course_from_article.pack.assemble import (
    _code_step_tests_executable,
    _infer_python_entrypoint,
)
from app.domain.course_from_article.practice.practice_routing import is_python_artifact_shim
from app.domain.course_strategies.code_templates import code_template_is_substantive
from studio_contracts.packs.step_dependencies import apply_code_step_dependencies

_RU_LETTER_RE = re.compile(r"[А-Яа-яЁё]")


def _normalize_quizzes(raw: object, *, count: int) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    quizzes: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        choices = item.get("choices")
        if not isinstance(choices, list) or len(choices) < 2:
            continue
        choice_texts = [str(choice).strip() for choice in choices[:4] if str(choice).strip()]
        if len(choice_texts) < 4:
            continue
        answer = _coerce_quiz_answer(item.get("answer"))
        if answer is None:
            continue
        question = (_as_str(item.get("question")) or "").strip()
        if len(question) < 12:
            continue
        quiz_id = _slug(_as_str(item.get("id")) or f"quiz-{index + 1}")
        if not quiz_id.startswith("quiz"):
            quiz_id = f"quiz-{quiz_id}"
        quizzes.append(
            {
                "id": quiz_id,
                "kind": "quiz",
                "title": _as_str(item.get("title")) or f"Check {index + 1}",
                "question": question,
                "choices": choice_texts[:4],
                "answer": answer,
            }
        )
        if len(quizzes) >= count:
            break
    return quizzes


def _coerce_quiz_answer(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if 0 <= raw <= 3 else None
    if isinstance(raw, float) and raw.is_integer():
        value = int(raw)
        return value if 0 <= value <= 3 else None
    if isinstance(raw, str):
        text = raw.strip()
        if text.isdigit():
            value = int(text)
            return value if 0 <= value <= 3 else None
        letter = text[:1].casefold()
        if letter in "abcd":
            return ord(letter) - ord("a")
    return None


def _pick_code_template(item: dict[str, object]) -> str:
    for key in ("template", "code", "starter_code", "starter", "solution_template"):
        if value := _as_str(item.get(key)):
            return value
    return ""


def _pick_code_tests(item: dict[str, object]) -> list[object]:
    for key in ("tests", "test_cases", "cases"):
        value = item.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
    single = item.get("test")
    if isinstance(single, dict):
        return [single]
    return single if isinstance(single, list) else []


def _normalize_code_tests(raw_tests: list[object]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for test in raw_tests:
        if not isinstance(test, dict):
            continue
        run = test.get("run")
        if isinstance(run, str) and run.strip():
            normalized.append({"run": run.strip()})
            continue
        if "input" not in test or "output" not in test:
            continue
        normalized.append({"input": test["input"], "output": test["output"]})
    return normalized


def _apply_code_checker(
    task: dict[str, object],
    *,
    checker: str,
    rubric: str,
    content: str,
    level: str,
    has_tests: bool,
) -> None:
    if checker == "llm" or not has_tests or not _code_step_tests_executable(task):
        task["checker"] = "llm"
        if rubric:
            task["rubric"] = rubric
        elif content:
            task["rubric"] = content[:500]
        else:
            task["rubric"] = f"Complete the {level} coding exercise."
    elif rubric:
        task["rubric"] = rubric


def _one_code_task(
    item: dict[str, object],
    *,
    index: int,
    runtime: str,
    runtime_version: str,
) -> dict[str, object] | None:
    levels = ("easy", "medium", "hard", "expert", "capstone")
    template = _pick_code_template(item)
    if not code_template_is_substantive(template):
        return None
    content = _as_str(item.get("content")) or ""
    checker = _as_str(item.get("checker")) or ""
    rubric = _as_str(item.get("rubric")) or ""
    normalized_tests = _normalize_code_tests(_pick_code_tests(item))
    allow_llm_only = checker == "llm" or bool(content) or bool(rubric)
    if not normalized_tests and not allow_llm_only:
        return None
    level = _as_str(item.get("level")) or levels[min(index, len(levels) - 1)]
    task_id = _slug(_as_str(item.get("id")) or f"code-{level}")
    if not task_id.startswith("code"):
        task_id = f"code-{task_id}"
    entrypoint = _as_str(item.get("entrypoint")) or _infer_python_entrypoint(template)
    setup = _as_str(item.get("setup"))
    task: dict[str, object] = {
        "id": task_id,
        "kind": "code",
        "title": _as_str(item.get("title")) or f"Task {level}",
        "content": content,
        "runtime": _as_str(item.get("runtime")) or runtime,
        "runtime_version": _as_str(item.get("runtime_version")) or runtime_version,
        "template": template,
        "tests": normalized_tests[:8],
    }
    if entrypoint:
        task["entrypoint"] = entrypoint
    if setup:
        task["setup"] = setup
    _apply_code_checker(
        task,
        checker=checker,
        rubric=rubric,
        content=content,
        level=level,
        has_tests=bool(normalized_tests),
    )
    if is_python_artifact_shim(template=template, content=content):
        return _open_task_from_code_shim(
            task_id=task_id,
            level=level,
            title=_as_str(item.get("title")) or f"Task {level}",
            content=content,
            rubric=rubric,
            runtime=_as_str(item.get("runtime")) or runtime,
        )
    apply_code_step_dependencies(task)
    return task


def _open_task_from_code_shim(
    *,
    task_id: str,
    level: str,
    title: str,
    content: str,
    rubric: str,
    runtime: str = "",
) -> dict[str, object]:
    open_id = (
        task_id.replace("code-", "task-", 1) if task_id.startswith("code-") else f"task-{level}"
    )
    brief = content.strip() or title
    ru = _RU_LETTER_RE.search(f"{title} {brief}") is not None
    if ru:
        answer_hint = (
            "**Как отвечать:** пришли запрошенный файл, конфигурацию или команды "
            "в формате статьи, а не функцию, которая возвращает их текст."
        )
        default_rubric = (
            "- Формат результата соответствует заданию и примерам статьи\n"
            "- Указанные шаги дают наблюдаемый требуемый результат\n"
            "- Нет программной обёртки, которая лишь возвращает текст артефакта"
        )
    else:
        answer_hint = (
            "**Response format:** submit the requested file, configuration, or commands "
            "in the article's format, not a function that returns their text."
        )
        default_rubric = (
            "- The deliverable format matches the task and source examples\n"
            "- The submitted steps produce the requested observable outcome\n"
            "- No code wrapper merely returns the artifact as text"
        )
    task: dict[str, object] = {
        "id": open_id,
        "kind": "task",
        "title": title,
        "content": f"{brief}\n\n{answer_hint}",
        "rubric": rubric or default_rubric,
        "checker": "llm",
    }
    if runtime_name := (runtime or "").strip():
        task["runtime"] = runtime_name
    return task


def _normalize_code_tasks(
    raw: object,
    *,
    count: int,
    runtime: str,
    runtime_version: str,
) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    tasks: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        task = _one_code_task(
            item,
            index=index,
            runtime=runtime,
            runtime_version=runtime_version,
        )
        if task is None:
            continue
        tasks.append(task)
        if len(tasks) >= count:
            break
    return tasks


def _normalize_open_tasks(raw: object, *, count: int, runtime: str = "") -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    levels = ["easy", "medium", "hard", "expert", "capstone"]
    tasks: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        content = _as_str(item.get("content"))
        rubric = _as_str(item.get("rubric")) or content
        if not content or not rubric:
            continue
        level = _as_str(item.get("level")) or levels[min(index, len(levels) - 1)]
        task_id = _slug(_as_str(item.get("id")) or f"task-{level}")
        if not task_id.startswith("task"):
            task_id = f"task-{task_id}"
        task: dict[str, object] = {
            "id": task_id,
            "kind": "task",
            "title": _as_str(item.get("title")) or f"Task {level}",
            "content": content,
            "rubric": rubric,
            "checker": "llm",
        }
        if runtime_name := (_as_str(item.get("runtime")) or runtime):
            task["runtime"] = runtime_name
        if exemplar := _as_str(item.get("exemplar")) or _as_str(item.get("answer")):
            task["exemplar"] = exemplar
        tasks.append(task)
        if len(tasks) >= count:
            break
    return tasks
