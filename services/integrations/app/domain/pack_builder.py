from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from studio_contracts.integration_schemas import ImportReport
from studio_contracts.normalized_pack import NormalizedPack, NormalizedStep, NormalizedTopic
from studio_contracts.pack import parse_manifest, validate_manifest


@dataclass(frozen=True, slots=True)
class BuiltPack:
    manifest: dict[str, object]
    disk_path: Path


def build_manifest(pack: NormalizedPack) -> dict[str, object]:
    topics = [
        {
            "id": topic.id,
            "title": topic.title,
            "phases": {
                "study": {"steps": topic.study},
                "practice": {"steps": topic.practice},
                "assess": {"steps": topic.assess},
            },
        }
        for topic in pack.topics
    ]
    steps = {step_id: _step_body(step) for step_id, step in pack.steps.items()}

    manifest: dict[str, object] = {
        "schema_version": 1,
        "id": pack.slug,
        "version": pack.version,
        "title": pack.title,
        "locale": pack.locale,
        "source": {"type": pack.platform, "course_id": pack.external_id},
        "defaults": {"runtime": "python", "runtime_version": "3.12"},
        "policies": {
            "skip_study_allowed": True,
            "assess_without_practice": False,
            "assess": {"max_attempts": 3, "autocomplete": False},
        },
        "topics": topics,
        "steps": steps,
    }
    if pack.course_assess:
        manifest["course_assess"] = {"steps": pack.course_assess}
    validate_manifest(manifest)
    return manifest


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
    _write_assets(version_dir, pack)
    return BuiltPack(manifest=manifest, disk_path=version_dir)


def summarize_report(report: ImportReport) -> ImportReport:
    if report.total_items == 0:
        fidelity = 0.0
    else:
        imported = report.imported_full + report.imported_partial * 0.5
        fidelity = round((imported / report.total_items) * 100, 1)
    return report.model_copy(update={"fidelity_percent": fidelity})


def normalized_from_adapter(payload: dict[str, object]) -> NormalizedPack:
    topics_raw = payload.get("topics")
    steps_raw = payload.get("steps")
    if not isinstance(topics_raw, list) or not isinstance(steps_raw, dict):
        msg = "adapter payload missing topics or steps"
        raise ValueError(msg)

    topics = [NormalizedTopic.model_validate(topic) for topic in topics_raw]
    steps = {
        key: NormalizedStep.model_validate(value)
        for key, value in steps_raw.items()
        if isinstance(key, str) and isinstance(value, dict)
    }
    course_assess: list[str] = []
    if isinstance(course_assess_raw := payload.get("course_assess"), list):
        course_assess = [str(item) for item in course_assess_raw if isinstance(item, str)]

    return NormalizedPack(
        platform=str(payload["platform"]),
        external_id=str(payload["external_id"]),
        title=str(payload["title"]),
        slug=str(payload["slug"]),
        version=str(payload.get("version", "1.0.0")),
        locale=str(payload.get("locale", "en")),
        topics=topics,
        steps=steps,
        course_assess=course_assess,
    )


def _step_body(step: NormalizedStep) -> dict[str, object]:
    body: dict[str, object] = {
        "kind": step.kind,
        "title": step.title,
        **step.payload,
    }
    if step.fidelity == "partial":
        body["fidelity"] = "partial"
    return body


def _write_assets(version_dir: Path, pack: NormalizedPack) -> None:
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
