from __future__ import annotations

import uuid

import structlog
from app.api.deps import DbSession, Settings
from app.api.mappers import build_course_digest, build_step_view
from app.api.session_views import build_session_state, session_position
from app.domain import messaging as session_messaging
from app.domain.analytics_events import analytics_event
from app.domain.session_passed import passed_step_ids
from app.domain.sessions import get_owned_session, navigate_session, skip_study
from fastapi import APIRouter
from studio_common.internal import InternalUserId
from studio_contracts.manifest import get_step
from studio_contracts.session_schemas import (
    CourseDigest,
    NavigateRequest,
    SessionState,
    StepContent,
)

router = APIRouter()
log = structlog.get_logger("sessions.study")


@router.get("/{session_id}/step", response_model=StepContent)
async def get_current_step(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> StepContent:
    learning_session = await get_owned_session(session, user_id, session_id)
    return build_step_view(learning_session)


@router.get("/{session_id}/course-digest", response_model=CourseDigest)
async def get_course_digest(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> CourseDigest:
    learning_session = await get_owned_session(session, user_id, session_id)
    return build_course_digest(learning_session)


@router.post("/{session_id}/navigate", response_model=SessionState)
async def navigate(
    session_id: uuid.UUID,
    body: NavigateRequest,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
) -> SessionState:
    before = await get_owned_session(session, user_id, session_id)
    previous = session_position(before)
    learning_session = await navigate_session(
        session,
        user_id,
        session_id,
        topic_id=body.topic,
        phase=body.phase,
        step_id=body.step,
        complete_current=body.complete_current,
    )
    events = []
    if body.complete_current:
        prev_topic, prev_phase, prev_step = previous
        step = get_step(before.manifest, prev_step)
        kind = step.get("kind")
        is_gradable = kind in {"quiz", "code", "lab", "task"}
        passed = await passed_step_ids(session, learning_session.id)
        if (not is_gradable) or prev_step in passed:
            events.append(
                analytics_event(
                    learning_session,
                    "step_completed",
                    topic_id=prev_topic,
                    phase=prev_phase,
                    step_id=prev_step,
                )
            )
    if session_position(learning_session) != previous:
        events.append(analytics_event(learning_session, "phase_entered"))
    if events:
        try:
            await session_messaging.publish_analytics_events(settings, events)
        except Exception as exc:
            log.warning(
                "navigate_analytics_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                session_id=str(session_id),
            )
    return await build_session_state(session, learning_session)


@router.post("/{session_id}/skip-study", response_model=SessionState)
async def skip_study_endpoint(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
) -> SessionState:
    learning_session = await skip_study(session, user_id, session_id)
    try:
        await session_messaging.publish_analytics_events(
            settings,
            [analytics_event(learning_session, "study_skipped", phase="study")],
        )
    except Exception as exc:
        log.warning(
            "skip_study_analytics_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            session_id=str(session_id),
        )
    return await build_session_state(session, learning_session)
