from __future__ import annotations

from app.api.routes.discovery.discover_course_map import course_summary_from_raw, to_course_summary
from app.infra.models import ExternalCourseCache
from studio_contracts.api.integration_schemas import ExternalCourseSummary

_DEMO_TITLES = frozenset(
    {
        "intro python",
        "exercism python track",
        "javascript algorithms",
    }
)
_FIXTURE_ONLY_PLATFORMS: frozenset[str] = frozenset()

__all__ = [
    "to_course_summary",
    "is_demo_course",
    "summaries_from_cache",
    "course_summary_from_raw",
    "filter_summaries",
]


def is_demo_course(row: ExternalCourseCache) -> bool:
    if row.title.casefold() in _DEMO_TITLES:
        return True
    return (
        row.platform_id in _FIXTURE_ONLY_PLATFORMS
        and row.external_id == "1"
        and not str((row.metadata_json or {}).get("author", "")).strip()
    )


def summaries_from_cache(rows: list[ExternalCourseCache]) -> list[ExternalCourseSummary]:
    return [to_course_summary(row) for row in rows if not is_demo_course(row)]


def filter_summaries(
    courses: list[ExternalCourseSummary],
    *,
    needle: str,
) -> list[ExternalCourseSummary]:
    if not needle:
        return courses
    lowered = needle.casefold()
    return [
        course
        for course in courses
        if lowered in course.title.casefold()
        or lowered in course.description.casefold()
        or lowered in course.platform.casefold()
        or any(lowered in tag.casefold() for tag in course.tags)
    ]
