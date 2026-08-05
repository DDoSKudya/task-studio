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

_LEGACY_DOMAIN_MAP: dict[str, CourseProfile] = {
    "code": "programming",
    "language": "language_learning",
    "general": "general",
}


def normalize_course_profile(raw: object, *, domain: str, title: str, corpus: str) -> CourseProfile:
    value = str(raw or "").strip().casefold().replace("-", "_")
    allowed: set[str] = {
        "programming",
        "data",
        "language_learning",
        "humanities",
        "business",
        "science_general",
        "general",
    }
    if value in allowed:
        return value  # type: ignore[return-value]

    legacy = _LEGACY_DOMAIN_MAP.get(domain.casefold())
    if legacy:
        return legacy

    blob = f"{title}\n{corpus[:6000]}".casefold()
    if any(token in blob for token in ("sql", "pandas", "dataset", "machine learning", "аналит")):
        return "data"
    if any(
        token in blob
        for token in (
            "english",
            "grammar",
            "vocabulary",
            "перевод",
            "английск",
            "ielts",
            "toefl",
            "язык",
        )
    ):
        return "language_learning"
    if any(token in blob for token in ("истори", "литератур", "философ", "humanities", "культур")):
        return "humanities"
    if any(token in blob for token in ("маркет", "бизнес", "management", "finance", "продаж")):
        return "business"
    if any(
        token in blob for token in ("def ", "class ", "function ", "python", "javascript", "api")
    ):
        return "programming"
    if any(token in blob for token in ("физик", "хими", "биолог", "наук", "science")):
        return "science_general"
    return "general"


def profile_skill_overlay(profile: str) -> str:
    mapping: dict[str, str] = {
        "programming": "domain-programming",
        "data": "domain-data",
        "language_learning": "domain-language-learning",
        "humanities": "domain-humanities",
        "business": "domain-business",
        "science_general": "domain-science",
        "general": "domain-general",
    }
    return mapping.get(profile, "domain-general")
