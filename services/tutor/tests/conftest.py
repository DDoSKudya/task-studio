from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent))


def legacy_course_config(builds_root: Path | None = None) -> SimpleNamespace:
    """Minimal tutor config for course pipeline tests (disk checkpoints + no Ollama stop)."""
    root = builds_root or Path("/tmp/task-studio-pytest-course-builds")
    root.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        course_topic_bundles=False,
        course_builds_root=root,
        course_build_ttl_days=14,
        ollama_url="",
        ollama_model="test-model",
    )


@pytest.fixture
def tutor_config(tmp_path: Path) -> SimpleNamespace:
    return legacy_course_config(tmp_path / "course-builds")
