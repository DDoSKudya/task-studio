from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from studio_contracts.studio_schemas import CourseDeviation, CourseFromArticleRequest

from .constants import _BAND_CONSISTENCY
from .messages import _consistency_user_message
from .normalize import _normalize_deviations
from .pipeline_hooks import _stage_json
from .progress import _stage_event
from .textutil import _as_str


@dataclass
class ConsistencyStageResult:
    deviations: list[CourseDeviation] = field(default_factory=list)
    halted: bool = False
    warning: str | None = None


async def iter_consistency_stage(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    sources: list[dict[str, object]],
    result: ConsistencyStageResult,
    band_consistency: tuple[float, float] = _BAND_CONSISTENCY,
) -> AsyncIterator[dict[str, object]]:
    yield _stage_event(
        stage="consistency",
        status="running",
        progress=band_consistency[0],
        message="Checking topic fit and contradictions across articles",
        message_key="consistencyChecking",
        detail={"article_count": len(sources)},
    )
    consistency = await _stage_json(
        client,
        target,
        compact=compact,
        stage="consistency",
        user_message=_consistency_user_message(body, sources),
        max_tokens=900 if compact else 1400,
    )
    deviations = _normalize_deviations(consistency.get("deviations"), sources)
    result.deviations = deviations
    related = consistency.get("related")
    if not isinstance(related, bool):
        related = len(deviations) == 0
    similarity = consistency.get("similarity")
    if not isinstance(similarity, int | float):
        similarity = 1.0 if related and not deviations else 0.5
    shared_topic = _as_str(consistency.get("shared_topic")) or ""

    yield _stage_event(
        stage="consistency",
        status="done",
        progress=band_consistency[1],
        message="Consistency check finished",
        message_key="consistencyDone",
        detail={
            "related": related,
            "similarity": float(similarity),
            "shared_topic": shared_topic,
            "deviations": [item.model_dump(mode="json") for item in deviations],
            "article_count": len(sources),
        },
    )

    needs_gate = (not related) or bool(deviations)
    if needs_gate and not body.ignore_deviations:
        result.halted = True
        yield {
            "type": "consistency_gate",
            "stage": "consistency",
            "status": "needs_confirmation",
            "progress": band_consistency[1],
            "message": "Articles differ — confirm to continue or cancel",
            "message_key": "consistencyGate",
            "detail": {
                "related": related,
                "similarity": float(similarity),
                "shared_topic": shared_topic,
                "deviations": [item.model_dump(mode="json") for item in deviations],
                "article_count": len(sources),
            },
        }
        return
    if needs_gate and body.ignore_deviations:
        result.warning = "continued despite article deviations"
