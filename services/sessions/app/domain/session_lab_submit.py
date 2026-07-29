from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from app.config import SessionsSettings
from app.domain.session_errors import SessionError, SubmitOutcome
from app.domain.session_grading_client import next_attempt_number, upstream_error_detail
from app.domain.session_lab_policy import lab_should_sync_llm
from app.infra.models import Attempt, Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.grading_schemas import GradingCheckResponse, GradingLabSubmitResponse

__all__ = ["lab_should_sync_llm", "submit_lab"]


async def submit_lab(
    session: AsyncSession,
    user_id: uuid.UUID,
    learning_session: Session,
    submission: dict[str, object],
    *,
    step: dict[str, object],
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> SubmitOutcome:
    attempt_number = await next_attempt_number(
        session,
        learning_session.id,
        learning_session.current_topic_id,
        learning_session.current_phase,
        learning_session.current_step_id,
    )
    attempt = Attempt(
        session_id=learning_session.id,
        user_id=user_id,
        topic_id=learning_session.current_topic_id,
        phase=learning_session.current_phase,
        step_id=learning_session.current_step_id,
        attempt_number=attempt_number,
        submission=submission,
        result={"status": "pending"},
    )
    session.add(attempt)
    await session.flush()

    try:
        response = await client.post(
            f"{settings.grading_service_url}/internal/v1/grading/lab",
            json={
                "step": step,
                "submission": {**submission, "attempt_id": str(attempt.id)},
                "user_id": str(user_id),
                "pack_version_id": str(learning_session.pack_version_id),
            },
        )
    except httpx.HTTPError as exc:
        raise SessionError(503, "grading unavailable") from exc
    if response.is_error:
        raise SessionError(response.status_code, upstream_error_detail(response))

    lab_response = GradingLabSubmitResponse.model_validate(response.json())
    grading = GradingCheckResponse(
        passed=False,
        score=0.0,
        feedback=None,
        details={"status": lab_response.status},
    )
    learning_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(attempt)
    return SubmitOutcome(
        attempt=attempt,
        grading=grading,
        phase_completed=False,
        status="pending",
    )
