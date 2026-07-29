from __future__ import annotations

from app.domain.pack.assets import step_body
from studio_contracts.normalized_pack import NormalizedPack
from studio_contracts.pack import validate_manifest


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
    steps = {
        step_id: step_body(step, platform=pack.platform) for step_id, step in pack.steps.items()
    }

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
