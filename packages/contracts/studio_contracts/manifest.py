from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PhaseName = Literal["study", "practice", "assess"]


@dataclass(frozen=True, slots=True)
class TopicRef:
    id: str
    title: str


@dataclass(frozen=True, slots=True)
class SessionPosition:
    topic_id: str
    phase: PhaseName
    step_id: str


@dataclass(frozen=True, slots=True)
class PackPolicies:
    skip_study_allowed: bool
    assess_without_practice: bool
    assess_max_attempts: int | None
    assess_autocomplete: bool


def list_topics(manifest: dict[str, object]) -> list[TopicRef]:
    raw_topics = manifest.get("topics")
    if not isinstance(raw_topics, list):
        msg = "manifest topics must be a list"
        raise ValueError(msg)

    topics: list[TopicRef] = []
    for item in raw_topics:
        if not isinstance(item, dict):
            continue
        topic_id = item.get("id")
        title = item.get("title")
        if isinstance(topic_id, str) and isinstance(title, str):
            topics.append(TopicRef(id=topic_id, title=title))
    if not topics:
        msg = "manifest has no topics"
        raise ValueError(msg)
    return topics


def phase_step_ids(
    manifest: dict[str, object],
    topic_id: str,
    phase: PhaseName,
) -> list[str]:
    topic = _find_topic(manifest, topic_id)
    phases = topic.get("phases")
    if not isinstance(phases, dict):
        return []
    phase_body = phases.get(phase)
    if not isinstance(phase_body, dict):
        return []
    steps = phase_body.get("steps")
    if not isinstance(steps, list):
        return []
    return [step_id for step_id in steps if isinstance(step_id, str)]


def get_step(manifest: dict[str, object], step_id: str) -> dict[str, object]:
    steps = manifest.get("steps")
    if not isinstance(steps, dict):
        msg = "manifest steps must be an object"
        raise ValueError(msg)
    step = steps.get(step_id)
    if not isinstance(step, dict):
        msg = f"unknown step {step_id!r}"
        raise ValueError(msg)
    return step


def first_position(manifest: dict[str, object]) -> SessionPosition:
    topic = list_topics(manifest)[0]
    for phase in ("study", "practice", "assess"):
        step_ids = phase_step_ids(manifest, topic.id, phase)
        if step_ids:
            return SessionPosition(topic_id=topic.id, phase=phase, step_id=step_ids[0])
    msg = "manifest has no steps"
    raise ValueError(msg)


def resolve_position(
    manifest: dict[str, object],
    topic_id: str,
    phase: PhaseName,
    step_id: str,
) -> SessionPosition:
    _find_topic(manifest, topic_id)
    step_ids = phase_step_ids(manifest, topic_id, phase)
    if step_id not in step_ids:
        msg = f"step {step_id!r} is not in {topic_id}/{phase}"
        raise ValueError(msg)
    get_step(manifest, step_id)
    return SessionPosition(topic_id=topic_id, phase=phase, step_id=step_id)


def practice_entry(manifest: dict[str, object], topic_id: str) -> SessionPosition:
    step_ids = phase_step_ids(manifest, topic_id, "practice")
    if not step_ids:
        msg = f"topic {topic_id!r} has no practice steps"
        raise ValueError(msg)
    return SessionPosition(topic_id=topic_id, phase="practice", step_id=step_ids[0])


def read_policies(manifest: dict[str, object]) -> PackPolicies:
    policies = manifest.get("policies")
    if not isinstance(policies, dict):
        return PackPolicies(
            skip_study_allowed=True,
            assess_without_practice=False,
            assess_max_attempts=None,
            assess_autocomplete=False,
        )

    assess = policies.get("assess")
    assess_body = assess if isinstance(assess, dict) else {}
    max_attempts = assess_body.get("max_attempts")
    is_int = isinstance(max_attempts, int) and not isinstance(max_attempts, bool)
    parsed_max = max_attempts if is_int else None
    autocomplete = assess_body.get("autocomplete")
    return PackPolicies(
        skip_study_allowed=policies.get("skip_study_allowed") is not False,
        assess_without_practice=policies.get("assess_without_practice") is True,
        assess_max_attempts=parsed_max,
        assess_autocomplete=autocomplete is True,
    )


def has_course_assess(manifest: dict[str, object]) -> bool:
    return isinstance(manifest.get("course_assess"), dict)


def _find_topic(manifest: dict[str, object], topic_id: str) -> dict[str, object]:
    raw_topics = manifest.get("topics")
    if not isinstance(raw_topics, list):
        msg = f"unknown topic {topic_id!r}"
        raise ValueError(msg)
    for item in raw_topics:
        if isinstance(item, dict) and item.get("id") == topic_id:
            return item
    msg = f"unknown topic {topic_id!r}"
    raise ValueError(msg)
