from __future__ import annotations

from studio_contracts.packs.normalized_pack import NormalizedPack, NormalizedStep, NormalizedTopic

from .normalize_step import coerce_adapter_step

_coerce_adapter_step = coerce_adapter_step


def normalized_from_adapter(payload: dict[str, object]) -> NormalizedPack:
    topics_raw = payload.get("topics")
    steps_raw = payload.get("steps")
    if not isinstance(topics_raw, list) or not isinstance(steps_raw, dict):
        msg = "adapter payload missing topics or steps"
        raise ValueError(msg)

    topics = [NormalizedTopic.model_validate(topic) for topic in topics_raw]
    phase_by_step = _phase_lookup(topics)
    steps = {
        key: NormalizedStep.model_validate(_coerce_adapter_step(value, phase_by_step.get(key)))
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


def _phase_lookup(topics: list[NormalizedTopic]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for topic in topics:
        for step_id in topic.study:
            mapping[step_id] = "study"
        for step_id in topic.practice:
            mapping[step_id] = "practice"
        for step_id in topic.assess:
            mapping[step_id] = "assess"
    return mapping
