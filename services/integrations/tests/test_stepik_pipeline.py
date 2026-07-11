from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from studio_contracts.integration_schemas import ImportReport
from studio_contracts.pack import validate_manifest
from studio_integration_sdk.registry import discover_adapters
from support import load_integrations_module


@pytest.fixture
def modules_root() -> Path:
    return Path(__file__).resolve().parents[3] / "integration_modules"


def test_discover_all_platform_adapters(modules_root: Path) -> None:
    adapters = discover_adapters(modules_root)
    assert set(adapters) == {"stepik", "exercism", "freecodecamp", "olx", "moodle"}


def test_stepik_fixture_import_builds_valid_manifest(modules_root: Path, tmp_path: Path) -> None:
    pack_builder = load_integrations_module("app.domain.pack_builder")
    adapter = discover_adapters(modules_root)["stepik"]
    pack_raw, report_raw = adapter.import_course(course_id="123")
    normalized = pack_builder.normalized_from_adapter(pack_raw)
    report = ImportReport.model_validate(report_raw)

    manifest = pack_builder.build_manifest(normalized)
    validate_manifest(manifest)

    built = pack_builder.write_pack_to_disk(
        normalized,
        packs_root=tmp_path,
        user_id=uuid.uuid4(),
    )
    assert (built.disk_path / "manifest.json").is_file()
    assert (built.disk_path / "videos" / "intro.mp4").is_file()
    assert report.total_items == len(normalized.steps)
    assert report.fidelity_percent == 0.0
    assert pack_builder.summarize_report(report).fidelity_percent == 87.5
    assert manifest["source"] == {"type": "stepik", "course_id": "123"}


def test_stepik_search_remote_matches_fixture(modules_root: Path) -> None:
    adapter = discover_adapters(modules_root)["stepik"]
    hits = adapter.search_remote(query="Python")
    assert hits
    assert hits[0]["id"] == "123"
