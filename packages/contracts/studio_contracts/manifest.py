from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, cast

PhaseName = Literal["study", "practice", "assess"]

DEFAULT_PHASE_ORDER: tuple[PhaseName, ...] = ("study", "practice", "assess")

ARTICLE_PHASE_ORDER: tuple[PhaseName, ...] = ("study", "assess", "practice")

_TASK_HEADING_RE = re.compile(r"задач[аеи]\s*\d+", re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(r"задани[ея]\s*:", re.IGNORECASE)
_WRITE_CODE_RE = re.compile(
    r"напишите\s+(запрос|код|функц|программ)|write\s+(a\s+)?(query|function|program|code)",
    re.IGNORECASE,
)
_CODEISH_RE = re.compile(
    r"\b(select|insert|update|delete|create\s+table|from|where|order\s+by|"
    r"def\s+\w+|class\s+\w+|function\s+\w+)\b",
    re.IGNORECASE,
)
_SQLISH_RE = re.compile(
    r"\b(select|insert|update|delete|create\s+table|join|group\s+by|order\s+by|"
    r"where|limit|offset|distinct|sql)\b",
    re.IGNORECASE,
)


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
    tutor_enabled: bool
    require_pass_to_advance: bool = True
    phase_order: tuple[PhaseName, ...] = DEFAULT_PHASE_ORDER


def normalize_phase_order(raw: object) -> tuple[PhaseName, ...]:
    if not isinstance(raw, list):
        return DEFAULT_PHASE_ORDER
    ordered: list[PhaseName] = []
    seen: set[str] = set()
    for item in raw:
        if item in {"study", "practice", "assess"} and item not in seen:
            ordered.append(cast(PhaseName, item))
            seen.add(item)
    for phase in DEFAULT_PHASE_ORDER:
        if phase not in seen:
            ordered.append(phase)
    return tuple(ordered)


def phase_order_for(manifest: dict[str, object]) -> tuple[PhaseName, ...]:
    return read_policies(manifest).phase_order


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
    if isinstance(phases, dict):
        phase_body = phases.get(phase)
        if isinstance(phase_body, dict):
            steps = phase_body.get("steps")
            if isinstance(steps, list):
                return [step_id for step_id in steps if isinstance(step_id, str)]

    flat = topic.get(phase)
    if isinstance(flat, list):
        return [step_id for step_id in flat if isinstance(step_id, str)]
    return []


def get_step(manifest: dict[str, object], step_id: str) -> dict[str, object]:
    steps = manifest.get("steps")
    if not isinstance(steps, dict):
        msg = "manifest steps must be an object"
        raise ValueError(msg)
    step = steps.get(step_id)
    if not isinstance(step, dict):
        msg = f"unknown step {step_id!r}"
        raise ValueError(msg)
    return repair_step(step)


def repair_step(step: dict[str, object]) -> dict[str, object]:
    kind = step.get("kind")
    if kind == "code":
        return step
    if kind != "theory" or not looks_like_coding_task(step):
        return step

    repaired = dict(step)
    repaired["kind"] = "code"
    runtime, version = infer_code_runtime(step)
    repaired.setdefault("runtime", runtime)
    repaired.setdefault("runtime_version", version)
    repaired.setdefault("template", "")
    repaired.setdefault("tests", [])
    return repaired


def looks_like_coding_task(step: dict[str, object]) -> bool:
    blob = _step_text_blob(step)
    if step.get("fidelity") == "partial" and (
        _TASK_HEADING_RE.search(blob) or "задани" in blob.casefold()
    ):
        return True
    if not (_ASSIGNMENT_RE.search(blob) or _WRITE_CODE_RE.search(blob)):
        return False
    return bool(_CODEISH_RE.search(blob))


def infer_code_runtime(step: dict[str, object]) -> tuple[str, str]:
    runtime = step.get("runtime")
    version = step.get("runtime_version")
    if isinstance(runtime, str) and runtime.strip():
        ver = version if isinstance(version, str) and version.strip() else "3.12"
        return runtime.strip(), ver
    if _SQLISH_RE.search(_step_text_blob(step)):
        return "sql", "15"
    return "python", "3.12"


def _step_text_blob(step: dict[str, object]) -> str:
    parts: list[str] = []
    for key in ("title", "instructions", "body_html", "question"):
        value = step.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return "\n".join(parts)


def first_position(manifest: dict[str, object]) -> SessionPosition:
    order = phase_order_for(manifest)
    for topic in list_topics(manifest):
        for phase in order:
            if step_ids := phase_step_ids(manifest, topic.id, phase):
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


def entry_after_phase(
    manifest: dict[str, object],
    topic_id: str,
    after_phase: PhaseName,
) -> SessionPosition:
    order = phase_order_for(manifest)
    try:
        start = order.index(after_phase) + 1
    except ValueError:
        start = 0
    for phase in order[start:]:
        if step_ids := phase_step_ids(manifest, topic_id, phase):
            return SessionPosition(topic_id=topic_id, phase=phase, step_id=step_ids[0])
    msg = f"topic {topic_id!r} has no steps after {after_phase}"
    raise ValueError(msg)


def iter_positions(manifest: dict[str, object]) -> list[SessionPosition]:
    positions: list[SessionPosition] = []
    order = phase_order_for(manifest)
    for topic in list_topics(manifest):
        for phase in order:
            for step_id in phase_step_ids(manifest, topic.id, phase):
                positions.append(SessionPosition(topic_id=topic.id, phase=phase, step_id=step_id))
    return positions


def adjacent_positions(
    manifest: dict[str, object],
    topic_id: str,
    phase: PhaseName,
    step_id: str,
) -> tuple[SessionPosition | None, SessionPosition | None]:
    positions = iter_positions(manifest)
    for index, position in enumerate(positions):
        if (
            position.topic_id == topic_id
            and position.phase == phase
            and position.step_id == step_id
        ):
            prev_pos = positions[index - 1] if index > 0 else None
            next_pos = positions[index + 1] if index + 1 < len(positions) else None
            return prev_pos, next_pos
    return None, None


def read_policies(manifest: dict[str, object]) -> PackPolicies:
    policies = manifest.get("policies")
    if not isinstance(policies, dict):
        return PackPolicies(
            skip_study_allowed=True,
            assess_without_practice=False,
            assess_max_attempts=None,
            assess_autocomplete=False,
            tutor_enabled=True,
            require_pass_to_advance=True,
            phase_order=DEFAULT_PHASE_ORDER,
        )

    assess = policies.get("assess")
    assess_body = assess if isinstance(assess, dict) else {}
    max_attempts = assess_body.get("max_attempts")
    is_int = isinstance(max_attempts, int) and not isinstance(max_attempts, bool)
    parsed_max = max_attempts if is_int else None
    autocomplete = assess_body.get("autocomplete")
    tutor = policies.get("tutor")
    tutor_body = tutor if isinstance(tutor, dict) else {}
    return PackPolicies(
        skip_study_allowed=policies.get("skip_study_allowed") is not False,
        assess_without_practice=policies.get("assess_without_practice") is True,
        assess_max_attempts=parsed_max,
        assess_autocomplete=autocomplete is True,
        tutor_enabled=tutor_body.get("enabled") is not False,
        require_pass_to_advance=policies.get("require_pass_to_advance") is not False,
        phase_order=normalize_phase_order(policies.get("phase_order")),
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
