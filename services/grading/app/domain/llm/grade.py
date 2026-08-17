from __future__ import annotations

import uuid

import httpx
from app.config import GradingSettings
from app.domain.check.outcome import CheckOutcome
from app.domain.llm.verdict import outcome_from_tutor_verdict
from studio_contracts.api.tutor_schemas import TutorGradeResponse

_GRADE_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)


async def try_llm_grade(
    client: httpx.AsyncClient,
    settings: GradingSettings,
    *,
    step: dict[str, object],
    submission: dict[str, object],
    kind: str,
    user_id: uuid.UUID | None,
    started: float,
    prior_feedback: str | None = None,
    prior_checker: str | None = None,
) -> CheckOutcome | None:
    if not settings.llm_grade_enabled:
        return None
    if user_id is None:
        return None

    headers = {"X-User-Id": str(user_id)}

    payload = {
        "kind": kind if kind in {"quiz", "code", "task", "lab"} else "task",
        "step": step,
        "submission": submission,
    }
    try:
        response = await client.post(
            f"{settings.tutor_service_url}/internal/v1/tutor/grade",
            headers=headers,
            json=payload,
            timeout=_GRADE_TIMEOUT,
        )
    except httpx.HTTPError:
        return None

    if response.is_error:
        return None

    try:
        verdict = TutorGradeResponse.model_validate(response.json())
    except (ValueError, TypeError):
        return None

    return outcome_from_tutor_verdict(
        verdict,
        started=started,
        min_confidence=settings.llm_grade_min_confidence,
        prior_feedback=prior_feedback,
        prior_checker=prior_checker,
    )
