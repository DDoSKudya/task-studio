from __future__ import annotations

from pathlib import Path

from studio_contracts.packs.pack_integrity import check_pack_integrity


def test_check_pack_integrity_ok(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    root.mkdir()
    (root / "manifest.json").write_text("{}", encoding="utf-8")
    lab = root / "lab"
    lab.mkdir()
    (lab / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
    manifest = {
        "steps": {
            "lab-1": {
                "kind": "lab",
                "compose_file": "lab/compose.yaml",
                "checks": [{"type": "http"}],
            },
            "theory-1": {"kind": "theory"},
        }
    }
    result = check_pack_integrity(str(root), manifest)
    assert result.ok
    assert result.issues == ()


def test_check_pack_integrity_missing_dir() -> None:
    result = check_pack_integrity("/tmp/does-not-exist-task-studio", {})
    assert result.status == "broken"
    assert "missing_pack_dir" in result.issues


def test_check_pack_integrity_missing_manifest_and_compose(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    root.mkdir()
    manifest = {
        "steps": {
            "lab-1": {
                "kind": "lab",
                "compose_file": "lab/compose.yaml",
                "checks": [{"type": "http"}],
            },
        }
    }
    result = check_pack_integrity(str(root), manifest)
    assert result.status == "broken"
    assert "missing_manifest" in result.issues
    assert "missing_compose:lab-1" in result.issues
