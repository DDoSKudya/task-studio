from __future__ import annotations

import json
from pathlib import Path

import pytest
from studio_contracts.fixtures import build_sample_pack_bytes
from studio_contracts.packs.pack import (
    extract_pack_archive,
    read_manifest_from_archive,
    validate_manifest,
    validate_pack_file,
)
from validate_pack import main

VALID_MANIFEST = {
    "schema_version": 1,
    "id": "sample-pack",
    "version": "1.0.0",
    "title": "Sample",
    "topics": [{"id": "topic-1", "title": "Intro", "phases": {}}],
    "steps": {"step-1": {"kind": "theory"}},
}


def test_validate_pack_accepts_valid_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
    validate_pack_file(manifest)


def test_validate_pack_rejects_invalid_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"title": "missing required fields"}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        validate_pack_file(manifest)


def test_validate_pack_rejects_invalid_json(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{not-json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_pack_file(manifest)


def test_read_manifest_from_sample_pack() -> None:
    parsed = read_manifest_from_archive(build_sample_pack_bytes())
    assert parsed.slug == "intro-python"
    steps = parsed.raw.get("steps")
    assert isinstance(steps, dict)
    code_step = steps.get("code-sum")
    assert isinstance(code_step, dict)
    assert code_step.get("kind") == "code"


def test_extract_pack_archive_writes_files(tmp_path: Path) -> None:
    parsed = extract_pack_archive(build_sample_pack_bytes(), tmp_path / "pack")
    assert parsed.slug == "intro-python"
    assert parsed.title == "Intro Python"
    assert (tmp_path / "pack" / "manifest.json").is_file()


def test_main_returns_2_when_args_missing() -> None:
    assert main([]) == 2


def test_main_returns_1_when_file_missing(tmp_path: Path) -> None:
    assert main([str(tmp_path / "missing.json")]) == 1


def test_main_returns_1_for_invalid_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"title": "missing required fields"}), encoding="utf-8")
    assert main([str(manifest)]) == 1


def test_main_returns_1_for_invalid_json(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{not-json", encoding="utf-8")
    assert main([str(manifest)]) == 1


def test_main_returns_0_for_valid_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
    assert main([str(manifest)]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_validate_manifest_rejects_missing_steps() -> None:
    broken = dict(VALID_MANIFEST)
    broken.pop("steps")
    with pytest.raises(ValueError, match="steps"):
        validate_manifest(broken)
