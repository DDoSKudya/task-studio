from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_parse_grade_json_accepts_fenced_payload() -> None:
    grade = load_service_module("app.domain.grade.payload")
    raw = """```json
{"passed": true, "confidence": 0.81, "feedback": "Верно", "rationale": "matches goal"}
```"""
    parsed = grade.parse_grade_json(raw)
    assert parsed is not None
    assert parsed["passed"] is True
    assert parsed["confidence"] == 0.81
    assert parsed["feedback"] == "Верно"


def test_parse_grade_json_rejects_bad_confidence() -> None:
    grade = load_service_module("app.domain.grade.payload")
    assert grade.parse_grade_json('{"passed": false, "confidence": 2, "feedback": "x"}') is None


def test_grade_system_prompt_is_grader_not_coach() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.grade_system_prompt(step_kind="quiz", step_title="Basics")
    assert "grader" in prompt.lower() or "grade" in prompt.lower()
    assert "JSON" in prompt
    assert "socratic" not in prompt.lower()
    assert "Basics" in prompt


def test_grade_skills_matrix() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    req = prompts.PromptRequest(
        mode="grade",
        phase=None,
        step_kind="code",
        step_title="SQL",
        compact=True,
        sql_aware=True,
    )
    skills = prompts.skills_for(req)
    assert "grade-json-contract" in skills
    assert "grade-duty" in skills
    assert "grade-code" in skills
    assert "grade-evidence" in skills
    assert "sql-coach" in skills
    assert "token-budget" in skills
    assert "socratic" not in skills


def test_grade_task_skills() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    req = prompts.PromptRequest(
        mode="grade",
        phase=None,
        step_kind="task",
        step_title="Essay",
        compact=False,
    )
    skills = prompts.skills_for(req)
    assert "grade-task" in skills
    assert "grade-code" not in skills
