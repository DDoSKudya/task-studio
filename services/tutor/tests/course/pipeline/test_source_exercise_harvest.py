from __future__ import annotations

from app.domain.course_from_article.common.content.textutil_scalars import _excerpt_balanced
from app.domain.course_from_article.curriculum.outline.normalize_outline import (
    _normalize_theory_step,
)
from app.domain.course_from_article.practice.source_exercise_harvest import (
    harvest_markdown_exercises,
    harvest_sources,
    strip_theory_exercise_sections,
)


def test_harvest_splits_assignment_and_keeps_teaching() -> None:
    md = """
# Docker mental model

Containers share the kernel.

## Как это работает на практике

Namespaces isolate processes.

## Задание: Сравниваем Docker и ВМ

1. Запустите контейнер.
2. Сравните с VM.

## Ответы на задание

Контейнер легче VM.

## Core idea

Images are layered filesystems.
""".strip()
    result = harvest_markdown_exercises(md, source_title="Docker")
    assert "Namespaces isolate" in result.teaching_markdown
    assert "Images are layered" in result.teaching_markdown
    assert "Задание: Сравниваем" not in result.teaching_markdown
    assert "Ответы на задание" not in result.teaching_markdown
    kinds = {item.kind for item in result.exercises}
    assert "practice" in kinds or "open" in kinds
    assert "answer_key" in kinds


def test_strip_theory_removes_leaked_homework() -> None:
    leaked = """
# Безопасность

Не запускайте от root.

## Задание 1: Просмотр логов

```bash
docker logs my_nginx
```

## Практическое задание: Ограничение ресурсов

Используйте `--memory`.
""".strip()
    cleaned = strip_theory_exercise_sections(leaked)
    assert "Не запускайте от root" in cleaned
    assert "Задание 1" not in cleaned
    assert "Практическое задание" not in cleaned
    assert "docker logs" not in cleaned


def test_normalize_theory_step_strips_exercises() -> None:
    chapter = {"id": "ch1", "title": "T", "source_excerpt": "x"}
    step = _normalize_theory_step(
        {
            "id": "theory-ch1",
            "title": "T",
            "content": "# T\n\nProse.\n\n## Задание: Quiz\n\nWhat is Docker?\n",
        },
        chapter,
    )
    assert "Prose" in str(step["content"])
    assert "Задание" not in str(step["content"])


def test_harvest_sources_rewrites_content() -> None:
    sources: list[dict[str, object]] = [
        {
            "title": "A",
            "content": "# Intro\n\nFact.\n\n## Exercise 1\n\nDo the thing.\n",
        }
    ]
    cleaned, seeds = harvest_sources(sources)
    assert "Fact" in str(cleaned[0]["content"])
    assert "Exercise 1" not in str(cleaned[0]["content"])
    assert seeds


def test_excerpt_balanced_keeps_middle_marker() -> None:
    text = "HEAD-" + ("a" * 2000) + "-MIDMARK-" + ("b" * 2000) + "-TAIL"
    out = _excerpt_balanced(text, 900)
    assert "HEAD-" in out
    assert "MIDMARK" in out
    assert "TAIL" in out or out.endswith("TAIL") or "b" in out
