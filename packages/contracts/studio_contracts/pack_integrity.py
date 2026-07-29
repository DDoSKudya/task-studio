from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PackIntegrityStatus = Literal["ok", "broken"]


@dataclass(frozen=True, slots=True)
class PackIntegrity:
    status: PackIntegrityStatus
    issues: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def check_pack_integrity(
    disk_path: str | None, manifest: dict[str, object] | None
) -> PackIntegrity:
                                                                      
    issues: list[str] = []
    if not disk_path or not str(disk_path).strip():
        return PackIntegrity(status="broken", issues=("missing_disk_path",))

    root = Path(disk_path)
    if not root.is_dir():
        return PackIntegrity(status="broken", issues=("missing_pack_dir",))

    if not (root / "manifest.json").is_file():
        issues.append("missing_manifest")

    if isinstance(manifest, dict):
        steps = manifest.get("steps")
        if isinstance(steps, dict):
            for step_id, step in steps.items():
                if not isinstance(step, dict) or step.get("kind") != "lab":
                    continue
                compose_file = step.get("compose_file")
                if not isinstance(compose_file, str) or not compose_file.strip():
                    issues.append(f"missing_compose:{step_id}")
                    continue
                if not (root / compose_file).is_file():
                    issues.append(f"missing_compose:{step_id}")

    if issues:
        return PackIntegrity(status="broken", issues=tuple(issues))
    return PackIntegrity(status="ok")
