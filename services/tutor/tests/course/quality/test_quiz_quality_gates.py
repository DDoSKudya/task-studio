from __future__ import annotations

from app.domain.course_from_article.local_course.policy.heuristics import quiz_item_is_usable
from app.domain.course_from_article.quality.assess_quality import quiz_is_usable
from app.domain.course_strategies import (
    choice_is_placeholder,
    dedupe_quiz_batch,
    quizzes_are_near_duplicates,
    stem_wants_many_answers,
)


def test_choice_placeholder_detects_prompt_examples() -> None:
    assert choice_is_placeholder("full text 2, Docker host") is True
    assert choice_is_placeholder("full text A") is True
    assert choice_is_placeholder("option B") is True
    assert choice_is_placeholder("Docker daemon") is False


def test_stem_rejects_select_all_that_apply() -> None:
    assert stem_wants_many_answers("Выберите все правильные ответы.") is True
    assert stem_wants_many_answers("Select all that apply.") is True
    assert stem_wants_many_answers("Какой компонент отвечает за логи?") is False


def test_quiz_is_usable_rejects_placeholder_and_multi_answer() -> None:
    bad = {
        "question": "Выберите все правильные ответы про Docker.",
        "choices": [
            "full text 1, Docker host",
            "full text 2, Docker daemon",
            "full text 3, client",
            "full text 4, compose",
        ],
        "answer": 1,
    }
    assert quiz_is_usable(bad) is False
    assert quiz_item_is_usable(bad, theory="Docker host daemon client", locale="ru") is False


def test_near_duplicate_quizzes_are_dropped() -> None:
    first = {
        "question": (
            "Какой компонент Docker перенаправляет stdout и stderr "
            "из контейнера в драйвер логирования?"
        ),
        "choices": ["host", "daemon", "client", "logging driver"],
        "answer": 3,
    }
    second = {
        "question": (
            "Какой компонент экосистемы Docker перенаправляет вывод "
            "стандартных потоков из контейнера в драйвер логирования?"
        ),
        "choices": ["host", "daemon", "client", "logging driver"],
        "answer": 3,
    }
    third = {
        "question": "Чем rootless-режим отличается от privileged?",
        "choices": ["root", "user", "rootless", "privileged"],
        "answer": 2,
    }
    assert quizzes_are_near_duplicates(first, second) is True
    assert quizzes_are_near_duplicates(first, third) is False
    kept = dedupe_quiz_batch([first, second, third])
    assert len(kept) == 2
    assert kept[0] is first
    assert kept[1] is third
