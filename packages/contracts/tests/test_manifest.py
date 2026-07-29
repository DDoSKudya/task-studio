from __future__ import annotations

import pytest
from studio_contracts.fixtures import build_sample_pack_bytes
from studio_contracts.manifest import (
    adjacent_positions,
    first_position,
    get_step,
    infer_code_runtime,
    iter_positions,
    list_topics,
    looks_like_coding_task,
    phase_step_ids,
    practice_entry,
    read_policies,
    repair_step,
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


def test_first_position_skips_empty_leading_topic() -> None:
    manifest: dict[str, object] = {
        "topics": [
            {
                "id": "empty",
                "title": "Empty",
                "phases": {
                    "study": {"steps": []},
                    "practice": {"steps": []},
                    "assess": {"steps": []},
                },
            },
            {
                "id": "ready",
                "title": "Ready",
                "phases": {
                    "study": {"steps": []},
                    "practice": {"steps": ["code-1"]},
                    "assess": {"steps": []},
                },
            },
        ],
        "steps": {"code-1": {"kind": "code", "title": "One"}},
    }
    position = first_position(manifest)
    assert position.topic_id == "ready"
    assert position.phase == "practice"
    assert position.step_id == "code-1"


def test_phase_step_ids_accepts_flat_adapter_topic() -> None:
    manifest: dict[str, object] = {
        "topics": [
            {
                "id": "t1",
                "title": "Topic",
                "study": ["theory-1"],
                "practice": ["code-1"],
                "assess": [],
            }
        ],
        "steps": {},
    }
    assert phase_step_ids(manifest, "t1", "study") == ["theory-1"]
    assert phase_step_ids(manifest, "t1", "practice") == ["code-1"]


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
    assert policies.tutor_enabled is True
    assert policies.require_pass_to_advance is True


def test_require_pass_to_advance_can_be_disabled() -> None:
    policies = read_policies({"policies": {"require_pass_to_advance": False}})
    assert policies.require_pass_to_advance is False


def test_phase_step_ids(sample_manifest: dict[str, object]) -> None:
    steps = phase_step_ids(sample_manifest, "basics", "assess")
    assert steps == ["quiz-types"]


def test_adjacent_positions_walks_linear_order(sample_manifest: dict[str, object]) -> None:
    positions = iter_positions(sample_manifest)
    assert len(positions) >= 2
    first = positions[0]
    prev_pos, next_pos = adjacent_positions(
        sample_manifest,
        first.topic_id,
        first.phase,
        first.step_id,
    )
    assert prev_pos is None
    assert next_pos == positions[1]


def test_repair_step_recovers_mislabeled_sql_task() -> None:
    step = {
        "kind": "theory",
        "title": "Фильтрация с WHERE. Простые условия",
        "fidelity": "partial",
        "instructions": "Задача 1: Фильтрация по точному совпадению (=)",
        "body_html": (
            "<p><strong>Задание:</strong> напишите запрос "
            "SELECT * FROM cadets WHERE squad = 'Alpha'</p>"
        ),
        "source_platform": "stepik",
        "external_step_id": "8356197",
    }
    assert looks_like_coding_task(step) is True
    repaired = repair_step(step)
    assert repaired["kind"] == "code"
    assert repaired["runtime"] == "sql"
    assert repaired["tests"] == []


def test_repair_step_keeps_plain_theory() -> None:
    step = {
        "kind": "theory",
        "title": "Назначение оператора WHERE",
        "instructions": "Запросы SELECT FROM извлекают все строки. WHERE фильтрует.",
        "body_html": "<p>Оператор WHERE позволяет сравнить значение в столбце.</p>",
    }
    assert looks_like_coding_task(step) is False
    assert repair_step(step)["kind"] == "theory"


def test_get_step_applies_repair() -> None:
    manifest: dict[str, object] = {
        "topics": [],
        "steps": {
            "step-1": {
                "kind": "theory",
                "fidelity": "partial",
                "instructions": "Задача 2: выбор столбцов",
                "body_html": "<p>SELECT name FROM cadets</p>",
            }
        },
    }
    assert get_step(manifest, "step-1")["kind"] == "code"
    assert infer_code_runtime(manifest["steps"]["step-1"]) == ("sql", "15")
