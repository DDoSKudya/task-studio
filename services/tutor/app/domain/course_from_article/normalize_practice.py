from __future__ import annotations

from .assemble import _code_step_tests_executable, _infer_python_entrypoint
from .textutil import _as_str, _slug


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
        while len(choice_texts) < 4:
            choice_texts.append(f"Option {len(choice_texts) + 1}")
        answer = item.get("answer")
        if not isinstance(answer, int) or isinstance(answer, bool) or answer < 0 or answer > 3:
            continue
        quiz_id = _slug(_as_str(item.get("id")) or f"quiz-{index + 1}")
        if not quiz_id.startswith("quiz"):
            quiz_id = f"quiz-{quiz_id}"
        quizzes.append(
            {
                "id": quiz_id,
                "kind": "quiz",
                "title": _as_str(item.get("title")) or f"Check {index + 1}",
                "question": _as_str(item.get("question")) or "Choose the correct statement.",
                "choices": choice_texts[:4],
                "answer": answer,
            }
        )
        if len(quizzes) >= count:
            break
    return quizzes


def _normalize_code_tasks(
    raw: object,
    *,
    count: int,
    runtime: str,
    runtime_version: str,
) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    levels = ["easy", "medium", "hard", "expert", "capstone"]
    tasks: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        template = _as_str(item.get("template"))
        tests = item.get("tests")
        if not template or not isinstance(tests, list) or len(tests) < 1:
            continue
        normalized_tests: list[dict[str, object]] = []
        for test in tests:
            if not isinstance(test, dict):
                continue
            run = test.get("run")
            if isinstance(run, str) and run.strip():
                normalized_tests.append({"run": run.strip()})
                continue
            if "input" not in test or "output" not in test:
                continue
            normalized_tests.append({"input": test["input"], "output": test["output"]})
        if len(normalized_tests) < 1:
            continue
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
            "content": _as_str(item.get("content")) or "",
            "runtime": _as_str(item.get("runtime")) or runtime,
            "runtime_version": _as_str(item.get("runtime_version")) or runtime_version,
            "template": template,
            "tests": normalized_tests[:8],
        }
        if entrypoint:
            task["entrypoint"] = entrypoint
        if setup:
            task["setup"] = setup
        checker = _as_str(item.get("checker"))
        rubric = _as_str(item.get("rubric"))
        if checker == "llm" or not _code_step_tests_executable(task):
            task["checker"] = "llm"
            if rubric:
                task["rubric"] = rubric
            elif content := _as_str(task.get("content")):
                task["rubric"] = content[:500]
        elif rubric:
            task["rubric"] = rubric
        tasks.append(task)
        if len(tasks) >= count:
            break
    return tasks


def _normalize_open_tasks(raw: object, *, count: int) -> list[dict[str, object]]:
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
        if exemplar := _as_str(item.get("exemplar")) or _as_str(
            item.get("answer")
        ):
            task["exemplar"] = exemplar
        tasks.append(task)
        if len(tasks) >= count:
            break
    return tasks
