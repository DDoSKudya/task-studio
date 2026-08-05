from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_split_long_theory_by_headings() -> None:
    split_mod = load_service_module("app.domain.course_from_article.theory_split")
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


def test_split_disabled_keeps_single_step() -> None:
    split_mod = load_service_module("app.domain.course_from_article.theory_split")
    steps = [
        {
            "id": "theory-x",
            "kind": "theory",
            "title": "X",
            "content": "## A\n" + ("x" * 5000),
        }
    ]
    assert split_mod.split_long_theory_steps(steps, enabled=False) == steps


def test_split_long_theory_caps_part_count() -> None:
    split_mod = load_service_module("app.domain.course_from_article.theory_split")
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
