from __future__ import annotations

from typing import Any


def optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def parse_catalog_course(course: dict[str, object]) -> dict[str, Any] | None:
    raw_id = course.get("external_id")
    if raw_id is None:
        raw_id = course.get("id")
    external_id = str(raw_id).strip() if raw_id is not None else ""
    title = course.get("title")
    if not external_id or not isinstance(title, str):
        return None
    description = course.get("description")
    author = course.get("author")
    language = course.get("language")
    tags_raw = course.get("tags")
    tags = (
        [str(tag) for tag in tags_raw if isinstance(tag, str) and tag.strip()]
        if isinstance(tags_raw, list)
        else []
    )
    return {
        "external_id": external_id,
        "title": title,
        "description": description if isinstance(description, str) else "",
        "author": author if isinstance(author, str) else "",
        "language": language if isinstance(language, str) else "",
        "tags": tags,
        "enrolled": optional_bool(course.get("enrolled")),
        "is_paid": optional_bool(course.get("is_paid")),
    }
