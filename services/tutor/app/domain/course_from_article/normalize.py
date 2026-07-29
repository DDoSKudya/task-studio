from __future__ import annotations

from .normalize_outline import (
    _normalize_book_spine,
    _normalize_chapters,
    _normalize_deviations,
    _normalize_domain,
    _normalize_theory_step,
)
from .normalize_practice import (
    _normalize_code_tasks,
    _normalize_open_tasks,
    _normalize_quizzes,
)

__all__ = [
    "_normalize_book_spine",
    "_normalize_chapters",
    "_normalize_code_tasks",
    "_normalize_deviations",
    "_normalize_domain",
    "_normalize_open_tasks",
    "_normalize_quizzes",
    "_normalize_theory_step",
]
