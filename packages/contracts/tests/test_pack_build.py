from __future__ import annotations

import json
import zipfile
from io import BytesIO

import pytest
from studio_contracts.packs.pack import (
    build_pack_archive,
    collect_manifest_errors,
    decode_build_assets,
)

LAB_MANIFEST = {
    "schema_version": 1,
    "id": "lab-pack",
    "version": "1.0.0",
    "title": "Lab Pack",
    "source": {"type": "local"},
    "topics": [{"id": "topic-1", "title": "Intro", "phases": {}}],
    "steps": {
        "lab-1": {
            "kind": "lab",
            "title": "Nginx lab",
            "compose_file": "lab/compose.yaml",
            "checks": [{"type": "command", "command": "true"}],
        }
    },
}


def test_collect_manifest_errors_flags_missing_lab_fields() -> None:
    broken = dict(LAB_MANIFEST)
    steps = dict(broken["steps"])  # type: ignore[index]
    steps["lab-1"] = {"kind": "lab", "title": "Broken"}
    broken["steps"] = steps
    issues = collect_manifest_errors(broken)
    paths = {issue.path for issue in issues}
    assert "steps.lab-1.compose_file" in paths
    assert "steps.lab-1.checks" in paths


def test_build_pack_archive_includes_manifest() -> None:
    archive = build_pack_archive(LAB_MANIFEST)
    with zipfile.ZipFile(BytesIO(archive)) as bundle:
        assert "manifest.json" in bundle.namelist()
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["id"] == "lab-pack"


def test_decode_build_assets_rejects_unsafe_paths() -> None:
    with pytest.raises(ValueError, match="unsafe asset path"):
        decode_build_assets([("../evil.txt", "dGVzdA==")])
