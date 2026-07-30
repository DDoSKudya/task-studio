from __future__ import annotations

from app.api.routes.discover_course_map import course_summary_from_raw
from app.domain.cache.parse import parse_catalog_course


def test_parse_catalog_course_keeps_paid_and_enrolled_flags() -> None:
    parsed = parse_catalog_course(
        {
            "external_id": "99",
            "title": "Paid SQL",
            "description": "d",
            "author": "a",
            "language": "ru",
            "tags": ["SQL"],
            "enrolled": False,
            "is_paid": True,
        }
    )
    assert parsed is not None
    assert parsed["enrolled"] is False
    assert parsed["is_paid"] is True


def test_course_summary_from_raw_keeps_paid_and_enrolled_flags() -> None:
    summary = course_summary_from_raw(
        {
            "platform": "stepik",
            "external_id": "10",
            "title": "Free course",
            "description": "",
            "enrolled": True,
            "is_paid": False,
        },
        platform_id="stepik",
    )
    assert summary is not None
    assert summary.enrolled is True
    assert summary.is_paid is False
