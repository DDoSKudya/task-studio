from __future__ import annotations

from typing import Literal

CourseProfile = Literal[
    "programming",
    "data",
    "language_learning",
    "humanities",
    "business",
    "science_general",
    "general",
]

CourseFamily = Literal[
    "technical",
    "humanities",
    "language",
    "business",
    "science",
    "general",
]

_PROFILES: tuple[CourseProfile, ...] = (
    "programming",
    "data",
    "language_learning",
    "humanities",
    "business",
    "science_general",
    "general",
)

_LEGACY_DOMAIN_MAP: dict[str, CourseProfile] = {
    "code": "programming",
    "language": "language_learning",
    "general": "general",
}

_FAMILY: dict[CourseProfile, CourseFamily] = {
    "programming": "technical",
    "data": "technical",
    "humanities": "humanities",
    "language_learning": "language",
    "business": "business",
    "science_general": "science",
    "general": "general",
}

_OVERLAY: dict[CourseProfile, str] = {
    "programming": "domain-programming",
    "data": "domain-data",
    "language_learning": "domain-language-learning",
    "humanities": "domain-humanities",
    "business": "domain-business",
    "science_general": "domain-science",
    "general": "domain-general",
}

_SIGNALS: dict[CourseProfile, tuple[tuple[str, int], ...]] = {
    "programming": (
        ("язык программирования", 6),
        ("programming language", 6),
        ("def ", 3),
        ("class ", 2),
        ("endpoint", 2),
        ("роутер", 3),
        ("декоратор", 3),
        ("import ", 1),
        ("фреймворк", 2),
        ("репозитор", 2),
        ("программирован", 3),
        ("http", 2),
        ("протокол", 2),
        ("version control", 4),
        ("branching", 3),
        ("merging", 2),
    ),
    "data": (
        ("machine learning", 5),
        ("dataframe", 5),
        ("dataset", 3),
        ("аналит", 2),
        ("container orchestration", 4),
        ("message queue", 3),
        ("observability", 3),
    ),
    "language_learning": (
        ("английск", 5),
        ("vocabulary", 4),
        ("grammar", 3),
        ("иностранн", 4),
        ("изучение языка", 5),
        ("subject/verb", 4),
        ("punctuation", 3),
        ("comma", 2),
    ),
    "humanities": (
        ("гуманитар", 5),
        ("философ", 4),
        ("литератур", 4),
        ("истори", 3),
        ("поэм", 3),
        ("культур", 2),
        ("humanities", 4),
        ("роман ", 2),
        ("bibliography", 2),
        ("epistemology", 4),
        ("virtue ethics", 4),
    ),
    "business": (
        ("management", 3),
        ("маркет", 3),
        ("продаж", 3),
        ("finance", 3),
        ("бизнес", 2),
        ("kpi", 3),
        ("unit-экономик", 4),
    ),
    "science_general": (
        ("физик", 3),
        ("хими", 3),
        ("биолог", 3),
        ("уравнен", 2),
        ("science", 2),
        ("наук", 1),
    ),
}


def _as_profile(value: str) -> CourseProfile | None:
    folded = value.strip().casefold().replace("-", "_")
    return next((item for item in _PROFILES if item == folded), None)


def course_family(profile: str) -> CourseFamily:
    return _FAMILY[_as_profile(profile) or "general"]


def practice_needs_code_starter(profile: str) -> bool:
    return course_family(profile) not in {"humanities", "language", "business", "science"}


def profile_skill_overlay(profile: str) -> str:
    return _OVERLAY[_as_profile(profile) or "general"]


def _score_blob(blob: str) -> dict[CourseProfile, int]:
    scores: dict[CourseProfile, int] = {item: 0 for item in _PROFILES}
    for profile, signals in _SIGNALS.items():
        for token, weight in signals:
            if token in blob:
                scores[profile] += weight
    if blob.count("```") >= 2:
        scores["programming"] += 3
    if "язык программирования" in blob or "programming language" in blob:
        scores["language_learning"] -= 4
    return scores


def detect_course_profile(*, title: str, corpus: str) -> CourseProfile:
    blob = f"{title}\n{title}\n{corpus[:8000]}".casefold()
    scores = _score_blob(blob)
    best_score = max(scores.values())
    if best_score < 3:
        return "general"
    tied: list[CourseProfile] = [profile for profile in _PROFILES if scores[profile] == best_score]

    priority: tuple[CourseProfile, ...] = (
        "language_learning",
        "humanities",
        "business",
        "science_general",
        "data",
        "programming",
        "general",
    )
    winner = tied[0]
    for profile in tied[1:]:
        if priority.index(profile) < priority.index(winner):
            winner = profile
    return winner


def normalize_course_profile(raw: object, *, domain: str, title: str, corpus: str) -> CourseProfile:
    hinted = _as_profile(str(raw or ""))
    detected = detect_course_profile(title=title, corpus=corpus)
    if hinted is not None:
        same_family = course_family(hinted) == course_family(detected)
        return hinted if detected in {"general", hinted} or same_family else detected
    legacy = _LEGACY_DOMAIN_MAP.get(str(domain or "").casefold())
    fallback = legacy if legacy is not None and legacy != "general" else detected
    return detected if detected != "general" else fallback
