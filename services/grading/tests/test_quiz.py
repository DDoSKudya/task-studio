from __future__ import annotations

import pytest
from app.domain.check import GradingError, grade_quiz


def test_grade_quiz_passes_correct_choice() -> None:
    step = {"kind": "quiz", "answer": 2}
    outcome = grade_quiz(step, {"choice_index": 2})
    assert outcome.passed is True
    assert outcome.score == 1.0


def test_grade_quiz_fails_wrong_choice() -> None:
    step = {"kind": "quiz", "answer": 2}
    outcome = grade_quiz(step, {"choice_index": 0})
    assert outcome.passed is False
    assert outcome.score == 0.0


def test_grade_quiz_requires_choice_index() -> None:
    with pytest.raises(GradingError, match="choice_index"):
        grade_quiz({"kind": "quiz", "answer": 1}, {})
