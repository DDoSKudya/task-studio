from __future__ import annotations

from typing import cast

from studio_contracts.api.session_schemas import OutlineStep, OutlineTopic
from studio_contracts.packs.manifest import (
    PhaseName,
    get_step,
    list_topics,
    phase_order_for,
    phase_step_ids,
)


def build_outline(manifest: dict[str, object]) -> list[OutlineTopic]:
    topics: list[OutlineTopic] = []
    order = phase_order_for(manifest)
    for topic_index, topic in enumerate(list_topics(manifest), start=1):
        steps: list[OutlineStep] = []
        lesson_index = 0
        for phase in order:
            for step_id in phase_step_ids(manifest, topic.id, phase):
                lesson_index += 1
                step = get_step(manifest, step_id)
                title = step.get("title")
                kind = step.get("kind")
                steps.append(
                    OutlineStep(
                        topic_id=topic.id,
                        phase=cast(PhaseName, phase),
                        step_id=step_id,
                        title=title if isinstance(title, str) and title.strip() else step_id,
                        kind=kind if isinstance(kind, str) else "unknown",
                        index_label=f"{topic_index}.{lesson_index}",
                    )
                )
        topics.append(
            OutlineTopic(
                topic_id=topic.id,
                title=topic.title,
                index=topic_index,
                steps=steps,
            )
        )
    return topics
