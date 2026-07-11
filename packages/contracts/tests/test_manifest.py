from __future__ import annotations

import pytest
from studio_contracts.fixtures import build_sample_pack_bytes
from studio_contracts.manifest import (
    first_position,
    list_topics,
    phase_step_ids,
    practice_entry,
    read_policies,
    resolve_position,
)
from studio_contracts.pack import read_manifest_from_archive


@pytest.fixture
def sample_manifest() -> dict[str, object]:
    return read_manifest_from_archive(build_sample_pack_bytes()).raw


def test_list_topics(sample_manifest: dict[str, object]) -> None:
    topics = list_topics(sample_manifest)
    assert len(topics) == 1
    assert topics[0].id == "basics"


def test_first_position(sample_manifest: dict[str, object]) -> None:
    position = first_position(sample_manifest)
    assert position.topic_id == "basics"
    assert position.phase == "study"
    assert position.step_id == "theory-hello"


def test_resolve_position(sample_manifest: dict[str, object]) -> None:
    position = resolve_position(sample_manifest, "basics", "practice", "code-sum")
    assert position.step_id == "code-sum"


def test_practice_entry(sample_manifest: dict[str, object]) -> None:
    position = practice_entry(sample_manifest, "basics")
    assert position.phase == "practice"


def test_read_policies(sample_manifest: dict[str, object]) -> None:
    policies = read_policies(sample_manifest)
    assert policies.skip_study_allowed is True
    assert policies.assess_max_attempts == 3
    assert policies.assess_autocomplete is False


def test_phase_step_ids(sample_manifest: dict[str, object]) -> None:
    steps = phase_step_ids(sample_manifest, "basics", "assess")
    assert steps == ["quiz-types"]
