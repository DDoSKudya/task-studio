from __future__ import annotations

import uuid

from app.api.deps import DbSession, Settings, UpstreamClient, load_progress
from app.api.mappers import (
    attempt_info,
    build_step_view,
    session_state,
    session_summary,
)
from app.domain.analytics_events import (
    analytics_event,
    step_completed_event,
    submit_event,
)
from app.domain.messaging import publish_analytics_events
from app.domain.sessions import (
    complete_attempt,
    get_owned_session,
    list_attempts,
    list_sessions,
    navigate_session,
    skip_study,
    start_session,
    submit_step,
)
from app.infra.models import Session
from fastapi import APIRouter, status
from studio_common.internal import InternalUserId
from studio_contracts.session_schemas import (
    AttemptCompleteRequest,
    AttemptInfo,
    NavigateRequest,
    SessionState,
    SessionSummary,
    StartSessionRequest,
    StepContent,
    SubmitRequest,
    SubmitResult,
)

router = APIRouter(prefix="/internal/v1/sessions", tags=["sessions"])


async def _build_session_state(session: DbSession, learning_session: Session) -> SessionState:
    progress_rows = await load_progress(session, learning_session.id)
    return session_state(learning_session, progress_rows)


def _session_position(learning_session: Session) -> tuple[str, str, str]:
    return (
        learning_session.current_topic_id,
        learning_session.current_phase,
        learning_session.current_step_id,
    )


@router.get("", response_model=list[SessionSummary])
async def list_user_sessions(user_id: InternalUserId, session: DbSession) -> list[SessionSummary]:
    rows = await list_sessions(session, user_id)
    return [session_summary(row) for row in rows]


@router.post("", response_model=SessionState, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: StartSessionRequest,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    client: UpstreamClient,
) -> SessionState:
    learning_session = await start_session(
        session,
        user_id,
        body.pack_version_id,
        settings=settings,
        client=client,
    )
    await publish_analytics_events(settings, [analytics_event(learning_session, "session_started")])
    return await _build_session_state(session, learning_session)


@router.get("/{session_id}", response_model=SessionState)
async def get_session(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> SessionState:
    learning_session = await get_owned_session(session, user_id, session_id)
    return await _build_session_state(session, learning_session)


@router.get("/{session_id}/step", response_model=StepContent)
async def get_current_step(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> StepContent:
    learning_session = await get_owned_session(session, user_id, session_id)
    return build_step_view(learning_session)


@router.post("/{session_id}/navigate", response_model=SessionState)
async def navigate(
    session_id: uuid.UUID,
    body: NavigateRequest,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
) -> SessionState:
    before = await get_owned_session(session, user_id, session_id)
    previous = _session_position(before)
    learning_session = await navigate_session(
        session,
        user_id,
        session_id,
        topic_id=body.topic,
        phase=body.phase,
        step_id=body.step,
    )
    if _session_position(learning_session) != previous:
        await publish_analytics_events(
            settings,
            [analytics_event(learning_session, "phase_entered")],
        )
    return await _build_session_state(session, learning_session)


@router.post("/{session_id}/skip-study", response_model=SessionState)
async def skip_study_endpoint(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
) -> SessionState:
    learning_session = await skip_study(session, user_id, session_id)
    await publish_analytics_events(
        settings,
        [analytics_event(learning_session, "study_skipped", phase="study")],
    )
    return await _build_session_state(session, learning_session)


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
    events = [submit_event(learning_session, outcome.attempt, outcome.grading)]
    if outcome.status == "completed":
        if completed := step_completed_event(learning_session, outcome.attempt, outcome.grading):
            events.append(completed)
    await publish_analytics_events(settings, events)
    return SubmitResult(
        attempt_id=outcome.attempt.id,
        status=outcome.status,
        passed=outcome.grading.passed,
        score=outcome.grading.score,
        feedback=outcome.grading.feedback,
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
        completed := step_completed_event(outcome.learning_session, outcome.attempt, outcome.grading)
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
