from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_parse_hint_lines_keeps_bullets() -> None:
    course_cache = load_service_module("app.domain.course.cache")
    raw = "- Start with SELECT\n* Check the WHERE clause\n3. Avoid full solutions"
    assert course_cache.parse_hint_lines(raw) == [
        "Start with SELECT",
        "Check the WHERE clause",
        "Avoid full solutions",
    ]


def test_format_course_outline_includes_index() -> None:
    course_cache = load_service_module("app.domain.course.cache")
    digest = course_cache.CourseDigest(
        pack_version_id="00000000-0000-0000-0000-000000000001",
        pack_title="SQL",
        steps=[
            course_cache.CourseDigestStep(
                step_id="s1",
                topic_id="t1",
                phase="practice",
                kind="code",
                title="Select all",
                index_label="1.2",
                text="Get rows from cadets",
                has_video=False,
            )
        ],
    )
    text = course_cache.format_course_outline(digest)
    assert "<course_outline>" in text
    assert "[1.2]" in text
    assert "Select all" in text


def test_step_page_text_includes_theory_md() -> None:
    course_cache = load_service_module("app.domain.course.cache")
    step = course_cache.StepContent(
        topic_id="t1",
        phase="study",
        step_id="s1",
        kind="theory",
        title="Intro",
        content={"theory_md": "Learn about hashing."},
    )
    assert "hashing" in course_cache.step_page_text(step)


def test_format_step_context_includes_starter_code() -> None:
    course_cache = load_service_module("app.domain.course.cache")
    digest = course_cache.CourseDigest(
        pack_version_id="00000000-0000-0000-0000-000000000001",
        pack_title="SQL",
        steps=[],
    )
    step = course_cache.StepContent(
        topic_id="t1",
        phase="practice",
        step_id="s1",
        kind="code",
        title="Sum",
        content={"instructions": "Return a + b"},
        editor={"template": "def solve(a, b):\n    pass\n", "runtime": "python"},
    )
    text = course_cache.format_step_context(digest, step)
    assert "Return a + b" in text
    assert "def solve" in text
    assert "<current_page>" in text
    assert "<page_content>" in text
    assert "<starter_code>" in text


def test_format_step_context_respects_page_limit() -> None:
    course_cache = load_service_module("app.domain.course.cache")
    digest = course_cache.CourseDigest(
        pack_version_id="00000000-0000-0000-0000-000000000001",
        pack_title="SQL",
        steps=[],
    )
    step = course_cache.StepContent(
        topic_id="t1",
        phase="study",
        step_id="s1",
        kind="theory",
        title="Long",
        content={"theory_md": "x" * 5000},
    )
    text = course_cache.format_step_context(digest, step, page_limit=200)
    assert "…" in text
    assert len(text) < 800
