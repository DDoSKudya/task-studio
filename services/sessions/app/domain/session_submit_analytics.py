from __future__ import annotations

import httpx
import structlog
from app.config import SessionsSettings
from app.domain import messaging as session_messaging
from app.domain.analytics_events import step_completed_event, submit_event
from app.domain.session_errors import SubmitOutcome
from app.infra.models import Session
from sqlalchemy.exc import SQLAlchemyError

log = structlog.get_logger("sessions.submit_analytics")


async def publish_submit_analytics(
    settings: SessionsSettings,
    learning_session: Session,
    outcome: SubmitOutcome,
) -> None:
    try:
        events = [
            submit_event(
                learning_session,
                outcome.attempt,
                outcome.grading,
                outcome_status=outcome.status,
            )
        ]
        if outcome.status == "completed" and (
            completed := step_completed_event(learning_session, outcome.attempt, outcome.grading)
        ):
            events.append(completed)
        await session_messaging.publish_analytics_events(settings, events)
    except (
        RuntimeError,
        httpx.HTTPError,
        SQLAlchemyError,
        OSError,
        ConnectionError,
        TimeoutError,
    ) as exc:
        log.warning(
            "submit_analytics_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            attempt_id=str(outcome.attempt.id),
        )
