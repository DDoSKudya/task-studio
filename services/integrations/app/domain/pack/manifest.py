from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.domain.pack.assets import step_body, write_assets
from app.domain.pack.manifest_build import build_manifest
from studio_contracts.integration_schemas import ImportReport
from studio_contracts.normalized_pack import NormalizedPack
from studio_contracts.pack import parse_manifest

_step_body = step_body
_write_assets = write_assets


@dataclass(frozen=True, slots=True)
class BuiltPack:
    manifest: dict[str, object]
    disk_path: Path


__all__ = [
    "BuiltPack",
    "build_manifest",
    "write_pack_to_disk",
    "summarize_report",
]


def write_pack_to_disk(
    pack: NormalizedPack,
    *,
    packs_root: Path,
    user_id: uuid.UUID,
) -> BuiltPack:
    manifest = build_manifest(pack)
    parsed = parse_manifest(manifest)
    pack_dir = packs_root / str(user_id) / str(uuid.uuid4())
    version_dir = pack_dir / parsed.version
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    write_assets(version_dir, pack)
    return BuiltPack(manifest=manifest, disk_path=version_dir)


def summarize_report(report: ImportReport) -> ImportReport:
    if report.total_items == 0:
        fidelity = 0.0
    else:
        imported = report.imported_full + report.imported_partial * 0.5
        fidelity = round((imported / report.total_items) * 100, 1)
    return report.model_copy(update={"fidelity_percent": fidelity})
