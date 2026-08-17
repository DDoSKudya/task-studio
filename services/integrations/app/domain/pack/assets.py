from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from studio_contracts.packs.normalized_pack import NormalizedPack, NormalizedStep


def step_body(step: NormalizedStep, *, platform: str = "") -> dict[str, object]:
    body: dict[str, object] = {
        "kind": step.kind,
        "title": step.title,
        **step.payload,
    }
    if step.fidelity == "partial":
        body["fidelity"] = "partial"
    if platform and "source_platform" not in body:
        body["source_platform"] = platform
    if "external_step_id" not in body and (match := re.fullmatch(r"step-(\d+)", step.id)):
        body["external_step_id"] = match[1]
    return body


def write_assets(version_dir: Path, pack: NormalizedPack) -> None:
    for step in pack.steps.values():
        asset_id = step.payload.get("asset_id")
        if not isinstance(asset_id, str):
            continue
        target = version_dir / asset_id
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"placeholder for {step.title}\nimported_at={datetime.now(UTC).isoformat()}\n",
            encoding="utf-8",
        )
