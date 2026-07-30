from __future__ import annotations

from app.domain.cache.parse import optional_bool
from app.infra.models import ExternalCourseCache
from studio_contracts.integration_schemas import ExternalCourseSummary


def coerce_tag_list(tags_raw: object) -> list[str]:
    if not isinstance(tags_raw, list):
        return []
    return [str(tag) for tag in tags_raw if isinstance(tag, str) and tag.strip()]


def to_course_summary(row: ExternalCourseCache) -> ExternalCourseSummary:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return ExternalCourseSummary(
        platform=row.platform_id,
        external_id=row.external_id,
        title=row.title,
        description=str(meta.get("description", "")),
        author=str(meta.get("author", "") or ""),
        language=str(meta.get("language", "") or ""),
        tags=coerce_tag_list(meta.get("tags")),
        enrolled=optional_bool(meta.get("enrolled")),
        is_paid=optional_bool(meta.get("is_paid")),
    )


def course_summary_from_raw(
    raw: dict[str, object], *, platform_id: str
) -> ExternalCourseSummary | None:
    raw_id = raw.get("external_id")
    if raw_id is None:
        raw_id = raw.get("id")
    summary = ExternalCourseSummary(
        platform=str(raw.get("platform") or platform_id),
        external_id=str(raw_id or ""),
        title=str(raw.get("title") or ""),
        description=str(raw.get("description") or ""),
        author=str(raw.get("author") or ""),
        language=str(raw.get("language") or ""),
        tags=coerce_tag_list(raw.get("tags")),
        enrolled=optional_bool(raw.get("enrolled")),
        is_paid=optional_bool(raw.get("is_paid")),
    )
    if not summary.external_id or not summary.title:
        return None
    return summary
