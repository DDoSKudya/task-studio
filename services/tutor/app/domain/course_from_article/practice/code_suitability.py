from __future__ import annotations

from app.domain.course_from_article.curriculum.outline.course_profile import CourseProfile


def code_suitability_score(*, profile: CourseProfile, runtime: str) -> float:
    scores: dict[CourseProfile, float] = {
        "programming": 0.95,
        "data": 0.9,
        "science_general": 0.55,
        "business": 0.35,
        "general": 0.4,
        "humanities": 0.15,
        "language_learning": 0.1,
    }
    base = scores.get(profile, 0.4)
    if runtime.strip():
        return min(1.0, base + 0.05)
    return base


def code_tasks_recommended(*, score: float, include_code: bool) -> bool:
    if not include_code:
        return False
    return score >= 0.45


def should_prompt_code_gate(*, score: float, include_code: bool, policy: str) -> bool:
    if not include_code:
        return False
    if policy == "auto_open" or policy == "auto_skip":
        return False
    return score < 0.45
