from __future__ import annotations

import uuid
from pathlib import Path

from app.domain.course_build.store import CourseBuildStore


def test_course_build_store_checkpoint_and_resume(tmp_path: Path) -> None:
    store = CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={
            "articles": [{"title": "A", "content": "x" * 80}],
            "title": "Pathlib",
            "include_theory": True,
            "include_quizzes": True,
            "include_code": True,
        },
        title="Pathlib",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)

    store.save_analyze(
        user_id,
        build_id,
        {
            "chapters": [{"id": "ch-1", "title": "One"}, {"id": "ch-2", "title": "Two"}],
            "book_spine": {"throughline": "x"},
            "outcomes": ["learn"],
            "domain": "python",
            "course_profile": "python",
            "pack_id": "pathlib",
            "title": "Pathlib",
            "locale": "ru",
        },
    )
    store.save_topic(
        user_id,
        build_id,
        "ch-1",
        theory={"id": "theory-ch-1", "title": "One", "content": "body"},
        quizzes=[{"id": "q1", "question": "?", "choices": ["a", "b"], "answer": 0}],
        codes=[],
    )
    store.patch_meta(
        user_id,
        build_id,
        status="paused",
        stage="topic_bundle",
        chapters_done=1,
        chapter_total=2,
        progress=0.4,
        message="paused",
    )

    listed = store.list_for_user(user_id)
    assert len(listed) == 1
    assert listed[0].chapters_done == 1
    assert store.list_topic_ids(user_id, build_id) == {"ch-1"}

    theory, quizzes, codes = store.load_topics(user_id, build_id)
    assert len(theory) == 1
    assert theory[0]["id"] == "theory-ch-1"
    assert len(quizzes) == 1
    assert codes == []

    request = store.load_request(user_id, build_id)
    assert request["title"] == "Pathlib"

    store.save_request(
        user_id,
        build_id,
        {**request, "ignore_deviations": True},
    )
    assert store.load_request(user_id, build_id)["ignore_deviations"] is True

    store.save_section_draft(
        user_id,
        build_id,
        "ch-1",
        index=1,
        total=2,
        content="draft one about routing",
    )
    store.save_section_draft(
        user_id,
        build_id,
        "ch-1",
        index=2,
        total=2,
        content="draft two about models",
    )
    drafts = store.load_section_drafts(user_id, build_id, "ch-1")
    assert drafts == ["draft one about routing", "draft two about models"]

    store.save_section_draft(
        user_id,
        build_id,
        "ch-2",
        index=1,
        total=4,
        content="only first window",
    )
    partial = store.load_section_drafts(user_id, build_id, "ch-2")
    assert partial[0] == "only first window"
    assert len(partial) == 4
    assert partial[1] == ""

    store.discard_section_drafts(user_id, build_id, "ch-1")
    assert store.load_section_drafts(user_id, build_id, "ch-1") == []

    store.discard(user_id, build_id)
    assert store.list_for_user(user_id) == []
