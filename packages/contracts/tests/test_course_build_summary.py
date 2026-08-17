from __future__ import annotations

import uuid

from studio_contracts.api.studio_schemas import CourseBuildDetail, CourseBuildSummary


def test_course_build_summary_accepts_uuid_string_from_json() -> None:

    summary = CourseBuildSummary.model_validate(
        {
            "build_id": "c128676c-8b79-42f4-9f07-81d234fe4597",
            "title": "Draft",
            "status": "running",
            "stage": "topic_bundle",
            "progress": 0.14,
            "message": "ok",
            "chapter_total": 3,
            "chapters_done": 0,
            "error": None,
            "created_at": "2026-08-04T12:00:00Z",
            "updated_at": "2026-08-04T12:00:00Z",
            "mode": "topic_bundles",
        }
    )
    assert summary.build_id == uuid.UUID("c128676c-8b79-42f4-9f07-81d234fe4597")


def test_course_build_summary_accepts_uuid_instance() -> None:
    build_id = uuid.uuid4()
    summary = CourseBuildSummary.model_validate(
        {
            "build_id": build_id,
            "title": "Draft",
            "status": "failed",
            "stage": "code",
            "progress": 0.5,
            "created_at": "2026-08-04T12:00:00Z",
            "updated_at": "2026-08-04T12:00:00Z",
        }
    )
    assert summary.build_id == build_id


def test_course_build_detail_includes_request() -> None:
    detail = CourseBuildDetail.model_validate(
        {
            "build_id": "c128676c-8b79-42f4-9f07-81d234fe4597",
            "title": "Draft",
            "status": "paused",
            "stage": "consistency",
            "progress": 0.1,
            "message": "gate",
            "chapter_total": 0,
            "chapters_done": 0,
            "error": None,
            "created_at": "2026-08-04T12:00:00Z",
            "updated_at": "2026-08-04T12:00:00Z",
            "mode": "topic_bundles",
            "request": {
                "articles": [{"title": "A", "content": "x" * 80}],
                "ignore_deviations": False,
            },
        }
    )
    articles = detail.request["articles"]
    assert isinstance(articles, list)
    assert isinstance(articles[0], dict)
    assert articles[0]["title"] == "A"
