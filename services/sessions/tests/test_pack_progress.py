from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def pack_progress(sessions_domain):
    del sessions_domain
    from app.domain import session_pack_progress

    return session_pack_progress


def test_chapter_title_from_manifest_prefers_topic_title(pack_progress) -> None:
    manifest = {"topics": [{"id": "t1", "title": " Intro Docker "}]}
    assert pack_progress.chapter_title_from_manifest(manifest, "t1") == "Intro Docker"
    assert pack_progress.chapter_title_from_manifest(manifest, "missing") == "missing"


def test_progress_percent_from_rows_weights_phases(pack_progress) -> None:
    from app.infra.models import PhaseProgress

    def row(
        *,
        study: bool = False,
        skipped: bool = False,
        practice: bool = False,
        assess: bool = False,
    ) -> PhaseProgress:
        item = MagicMock(spec=PhaseProgress)
        item.study_completed = study
        item.study_skipped = skipped
        item.practice_completed = practice
        item.assess_completed = assess
        return item

    rows = [
        row(study=True, practice=True),
        row(),
    ]
    assert pack_progress.progress_percent_from_rows(rows) == 33
    assert pack_progress.progress_percent_from_rows([]) == 0
