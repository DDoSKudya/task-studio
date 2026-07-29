from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.infra.models import Attempt, Session
from studio_contracts.analytics_schemas import AnalyticsEventMessage
from studio_contracts.grading_schemas import GradingCheckResponse
from studio_contracts.manifest import get_step


def analytics_event(
    learning_session: Session,
    event_type: str,
    *,
    topic_id: str | None = None,
    phase: str | None = None,
    step_id: str | None = None,
    payload: dict[str, object] | None = None,
) -> AnalyticsEventMessage:
    return AnalyticsEventMessage(
        event_id=uuid.uuid4(),
        event_type=event_type,
        user_id=learning_session.user_id,
        session_id=learning_session.id,
        pack_version_id=learning_session.pack_version_id,
        pack_title=learning_session.pack_title,
        topic_id=topic_id or learning_session.current_topic_id,
        phase=phase or learning_session.current_phase,
        step_id=step_id or learning_session.current_step_id,
        payload=payload or {},
        event_time=datetime.now(UTC),
    )


def submit_event(
    learning_session: Session,
    attempt: Attempt,
    grading: GradingCheckResponse,
) -> AnalyticsEventMessage:
    step = get_step(learning_session.manifest, attempt.step_id)
    match step.get("kind"):
        case "quiz":
            event_type = "quiz_answered"
        case "lab":
            event_type = "lab_submitted"
        case "task":
            event_type = "task_submitted"
        case _:
            event_type = "code_submitted"
    return analytics_event(
        learning_session,
        event_type,
        topic_id=attempt.topic_id,
        phase=attempt.phase,
        step_id=attempt.step_id,
        payload={
            "attempt_id": str(attempt.id),
            "passed": grading.passed,
            "score": grading.score,
            "attempt_number": attempt.attempt_number,
        },
    )


def step_completed_event(
    learning_session: Session,
    attempt: Attempt,
    grading: GradingCheckResponse,
) -> AnalyticsEventMessage | None:
    if not grading.passed:
        return None
    return analytics_event(
        learning_session,
        "step_completed",
        topic_id=attempt.topic_id,
        phase=attempt.phase,
        step_id=attempt.step_id,
        payload={
            "attempt_id": str(attempt.id),
            "score": grading.score,
        },
    )
