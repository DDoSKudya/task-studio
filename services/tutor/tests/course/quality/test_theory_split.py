from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_split_long_theory_by_headings() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    body = "\n\n".join(
        [
            "## Один",
            "a" * 800,
            "## Два",
            "b" * 800,
            "## Три",
            "c" * 800,
            "## Четыре",
            "d" * 800,
        ]
    )
    steps = [
        {
            "id": "theory-intro",
            "kind": "theory",
            "title": "Intro",
            "chapter_id": "intro",
            "content": body,
        }
    ]
    split = split_mod.split_long_theory_steps(steps, enabled=True, max_chars=1200)
    assert len(split) >= 2
    assert all(item["chapter_id"] == "intro" for item in split)
    assert split[0]["id"] == "theory-intro"
    assert split[1]["id"] == "theory-intro-2"


def test_split_long_theory_keeps_images_only_on_matching_part() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    figure = "https://cdn.example.com/images/arch.png"
    body = "\n\n".join(
        [
            "## One",
            "a" * 800,
            f"![diagram]({figure})",
            "## Two",
            "b" * 800,
        ]
    )
    steps = [
        {
            "id": "theory-intro",
            "kind": "theory",
            "title": "Intro",
            "images": [figure],
            "content": body,
        }
    ]
    split = split_mod.split_long_theory_steps(steps, enabled=True, max_chars=900)
    assert len(split) >= 2
    parts_with_images = [item for item in split if item.get("images")]
    assert len(parts_with_images) == 1
    assert parts_with_images[0]["images"] == [figure]


def test_split_disabled_keeps_single_step() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    steps = [
        {
            "id": "theory-x",
            "kind": "theory",
            "title": "X",
            "content": "## A\n" + ("x" * 5000),
        }
    ]
    assert split_mod.split_long_theory_steps(steps, enabled=False) == steps


def test_split_disabled_keeps_near_duplicate_titles_across_chapters() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    steps = [
        {
            "id": "t1",
            "kind": "theory",
            "title": "Архитектура!",
            "chapter_id": "ch-1",
            "content": "one",
        },
        {
            "id": "t2",
            "kind": "theory",
            "title": "Архитектура",
            "chapter_id": "ch-2",
            "content": "two",
        },
    ]
    out = split_mod.split_long_theory_steps(steps, enabled=False)
    assert len(out) == 2


def test_dedupe_theory_scopes_by_chapter_id() -> None:
    dedupe = load_service_module("app.domain.course_from_article.quality.theory_dedupe")
    steps = [
        {"id": "t1", "kind": "theory", "title": "Архитектура", "chapter_id": "a", "content": "1"},
        {"id": "t2", "kind": "theory", "title": "Архитектура!", "chapter_id": "b", "content": "2"},
        {"id": "t3", "kind": "theory", "title": "Архитектура", "chapter_id": "a", "content": "3"},
    ]
    out = dedupe.dedupe_theory_steps(steps)
    assert len(out) == 2
    assert {item["chapter_id"] for item in out} == {"a", "b"}


def test_split_long_theory_caps_part_count() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    sections = []
    for index in range(1, 20):
        sections.append(f"## Часть {index}")
        sections.append("x" * 900)
    steps = [
        {
            "id": "theory-fat",
            "kind": "theory",
            "title": "Fat",
            "chapter_id": "fat",
            "content": "\n\n".join(sections),
        }
    ]
    split = split_mod.split_long_theory_steps(steps, enabled=True, max_chars=1000, max_parts=6)
    assert 2 <= len(split) <= 6
    assert split[0]["id"] == "theory-fat"


def test_split_dedupes_duplicate_part_titles() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    body = "\n\n".join(
        [
            "## Одна тема",
            "a" * 2000,
            "## Одна тема",
            "b" * 2000,
            "## Одна тема",
            "c" * 2000,
        ]
    )
    steps = [
        {
            "id": "theory-dup",
            "kind": "theory",
            "title": "Глава",
            "content": body,
        }
    ]
    split = split_mod.split_long_theory_steps(steps, enabled=True, max_chars=800, max_parts=6)
    assert len(split) == 1
    assert split[0]["title"] == "Одна тема"


def test_split_uses_chapter_title_for_generic_conclusion() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    body = "\n\n".join(
        [
            "## Структурирование кода",
            "a" * 900,
            "## Заключение",
            "b" * 900,
            "## Структурирование кода",
            "c" * 900,
        ]
    )
    steps = [
        {
            "id": "theory-modules",
            "kind": "theory",
            "title": "Модули и структура",
            "content": body,
        }
    ]
    split = split_mod.split_long_theory_steps(steps, enabled=True, max_chars=1000)
    titles = [item["title"] for item in split]
    assert titles[0] == "Структурирование кода"
    assert titles[1] == "Модули и структура (2)"
    assert "Заключение" not in titles


def test_split_absorbs_thin_wrapup_into_previous_part() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    body = "\n\n".join(
        [
            "## Что такое Docker?",
            "a" * 900,
            "## Итог",
            "Теперь ты знаешь основные концепции Docker и его преимущества.",
        ]
    )
    steps = [
        {
            "id": "theory-docker",
            "kind": "theory",
            "title": "Что такое Docker?",
            "content": body,
        }
    ]
    split = split_mod.split_long_theory_steps(steps, enabled=True, max_chars=700)
    assert len(split) == 1
    content = str(split[0]["content"])
    assert "Теперь ты знаешь" in content
    assert len(content) >= 420
