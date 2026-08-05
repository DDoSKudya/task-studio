from __future__ import annotations

from dataclasses import dataclass

THEORY_STEP_KINDS = frozenset({"theory"})
VIDEO_STEP_KINDS = frozenset({"video"})
QUIZ_STEP_KINDS = frozenset({"quiz"})
PRACTICE_STEP_KINDS = frozenset({"code", "lab", "task"})


@dataclass(frozen=True, slots=True)
class PackContentModules:
    has_theory: bool = False
    has_video: bool = False
    has_quiz: bool = False
    has_practice: bool = False


def content_modules_from_manifest(manifest: dict[str, object] | None) -> PackContentModules:
    if not isinstance(manifest, dict):
        return PackContentModules()

    steps = manifest.get("steps")
    if not isinstance(steps, dict):
        return PackContentModules()

    has_theory = False
    has_video = False
    has_quiz = False
    has_practice = False

    for step in steps.values():
        if not isinstance(step, dict):
            continue
        kind = step.get("kind")
        if not isinstance(kind, str):
            continue
        if kind in THEORY_STEP_KINDS:
            has_theory = True
        elif kind in VIDEO_STEP_KINDS:
            has_video = True
        elif kind in QUIZ_STEP_KINDS:
            has_quiz = True
        elif kind in PRACTICE_STEP_KINDS:
            has_practice = True

    return PackContentModules(
        has_theory=has_theory,
        has_video=has_video,
        has_quiz=has_quiz,
        has_practice=has_practice,
    )
