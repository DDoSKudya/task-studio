from __future__ import annotations

import uuid

from app.api.deps import DbSession, Settings, UpstreamClient
from app.api.mappers import attempt_info
from app.domain.analytics_events import step_completed_event
from app.domain.messaging import publish_analytics_events
from app.domain.session_submit_analytics import publish_submit_analytics
from app.domain.sessions import complete_attempt, get_owned_session, list_attempts, submit_step
from fastapi import APIRouter, status
from studio_common.internal import InternalUserId
from studio_contracts.session_schemas import (
    AttemptCompleteRequest,
    AttemptInfo,
    SubmitRequest,
    SubmitResult,
)

router = APIRouter()


@router.post("/{session_id}/submit", response_model=SubmitResult)
async def submit(
    session_id: uuid.UUID,
    body: SubmitRequest,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    client: UpstreamClient,
) -> SubmitResult:
    learning_session = await get_owned_session(session, user_id, session_id)
    outcome = await submit_step(
        session,
        user_id,
        session_id,
        body.submission,
        settings=settings,
        client=client,
    )
    await publish_submit_analytics(settings, learning_session, outcome)
    return SubmitResult(
        attempt_id=outcome.attempt.id,
        status=outcome.status,
        passed=outcome.grading.passed,
        score=outcome.grading.score,
        feedback=outcome.grading.feedback,
        details=outcome.grading.details,
        phase_completed=outcome.phase_completed,
    )


@router.post("/attempts/{attempt_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_attempt_endpoint(
    attempt_id: uuid.UUID,
    body: AttemptCompleteRequest,
    session: DbSession,
    settings: Settings,
) -> None:
    outcome = await complete_attempt(
        session,
        attempt_id,
        passed=body.passed,
        score=body.score,
        feedback=body.feedback,
        details=body.details,
    )
    if outcome.learning_session is not None and (
        completed := step_completed_event(
            outcome.learning_session,
            outcome.attempt,
            outcome.grading,
        )
    ):
        await publish_analytics_events(settings, [completed])


@router.get("/{session_id}/attempts", response_model=list[AttemptInfo])
async def get_attempts(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> list[AttemptInfo]:
    rows = await list_attempts(session, user_id, session_id)
    return [attempt_info(row) for row in rows]
