from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import structlog
from app.config import SessionsSettings
from app.infra.models import Attempt, CourseAssessSession, PhaseProgress, Session
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.catalog_schemas import PackVersionContext
from studio_contracts.grading_schemas import GradingCheckResponse
from studio_contracts.manifest import (
    PackPolicies,
    PhaseName,
    SessionPosition,
    first_position,
    get_step,
    has_course_assess,
    list_topics,
    practice_entry,
    read_policies,
    resolve_position,
)

log = structlog.get_logger("sessions")


class SessionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class SubmitOutcome:
    attempt: Attempt
    grading: GradingCheckResponse
    phase_completed: bool


async def fetch_pack_version(
    client: httpx.AsyncClient,
    settings: SessionsSettings,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> PackVersionContext:
    try:
        response = await client.get(
            f"{settings.catalog_service_url}/internal/v1/catalog/pack-versions/{pack_version_id}",
            headers={"X-User-Id": str(user_id)},
        )
    except httpx.HTTPError as exc:
        raise SessionError(503, "catalog unavailable") from exc
    if response.status_code == 404:
        raise SessionError(404, "pack version not found")
    if response.is_error:
        raise SessionError(502, "catalog error")
    return PackVersionContext.model_validate(response.json())


async def start_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
    *,
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> Session:
    pack_context = await fetch_pack_version(client, settings, user_id, pack_version_id)
    try:
        position = first_position(pack_context.manifest)
    except ValueError as exc:
        raise SessionError(422, str(exc)) from exc

    now = datetime.now(UTC)
    learning_session = Session(
        user_id=user_id,
        pack_version_id=pack_version_id,
        pack_title=pack_context.pack_title,
        status="active",
        current_topic_id=position.topic_id,
        current_phase=position.phase,
        current_step_id=position.step_id,
        manifest=pack_context.manifest,
        started_at=now,
        updated_at=now,
    )
    session.add(learning_session)
    await session.flush()
    session.add(PhaseProgress(session_id=learning_session.id, topic_id=position.topic_id))
    if has_course_assess(pack_context.manifest):
        session.add(
            CourseAssessSession(
                session_id=learning_session.id,
                user_id=user_id,
                status="pending",
            )
        )
    await session.commit()
    await session.refresh(learning_session)
    return learning_session


async def get_owned_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session:
    learning_session = await session.get(Session, session_id)
    if learning_session is None or learning_session.user_id != user_id:
        raise SessionError(404, "session not found")
    return learning_session


def _require_active(learning_session: Session) -> None:
    if learning_session.status != "active":
        raise SessionError(409, "session is not active")


async def list_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[Session]:
    result = await session.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.updated_at.desc())
    )
    return list(result.scalars())


async def navigate_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    topic_id: str,
    phase: PhaseName,
    step_id: str,
) -> Session:
    learning_session = await get_owned_session(session, user_id, session_id)
    _require_active(learning_session)

    try:
        position = resolve_position(learning_session.manifest, topic_id, phase, step_id)
    except ValueError as exc:
        raise SessionError(422, str(exc)) from exc

    progress = await _get_or_create_progress(session, learning_session.id, topic_id)
    policies = read_policies(learning_session.manifest)
    assess_blocked = (
        phase == "assess"
        and not policies.assess_without_practice
        and not progress.practice_completed
    )
    if assess_blocked:
        raise SessionError(403, "practice must be completed before assess")

    if phase == "practice" and learning_session.current_phase == "study":
        progress.study_completed = True

    _apply_position(learning_session, position)
    await session.commit()
    await session.refresh(learning_session)
    return learning_session


async def skip_study(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session:
    learning_session = await get_owned_session(session, user_id, session_id)
    _require_active(learning_session)

    policies = read_policies(learning_session.manifest)
    if not policies.skip_study_allowed:
        raise SessionError(403, "study skip is not allowed")

    topic_id = learning_session.current_topic_id
    progress = await _get_or_create_progress(session, learning_session.id, topic_id)
    progress.study_skipped = True
    progress.study_completed = True

    try:
        position = practice_entry(learning_session.manifest, topic_id)
    except ValueError as exc:
        raise SessionError(422, str(exc)) from exc

    _apply_position(learning_session, position)
    await session.commit()
    await session.refresh(learning_session)

    log.info(
        "study_skipped",
        session_id=str(learning_session.id),
        user_id=str(user_id),
        topic_id=topic_id,
    )
    return learning_session


async def submit_step(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    submission: dict[str, object],
    *,
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> SubmitOutcome:
    learning_session = await get_owned_session(session, user_id, session_id)
    _require_active(learning_session)

    step = get_step(learning_session.manifest, learning_session.current_step_id)
    kind = step.get("kind")
    if kind not in {"quiz", "code"}:
        raise SessionError(422, "current step is not submittable")

    policies = read_policies(learning_session.manifest)
    if learning_session.current_phase == "assess":
        await _ensure_assess_attempt_allowed(session, learning_session, policies)

    attempt_number = await _next_attempt_number(
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
    )
    session.add(attempt)
    await session.flush()

    grading = await _call_grading(
        client,
        settings,
        step=step,
        submission={**submission, "attempt_id": str(attempt.id)},
    )
    attempt.result = grading.model_dump(mode="json")
    phase_completed = await _apply_grading_result(session, learning_session, grading)
    learning_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(attempt)
    return SubmitOutcome(attempt=attempt, grading=grading, phase_completed=phase_completed)


async def list_attempts(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> list[Attempt]:
    learning_session = await get_owned_session(session, user_id, session_id)
    result = await session.execute(
        select(Attempt)
        .where(Attempt.session_id == learning_session.id)
        .order_by(Attempt.created_at.desc())
    )
    return list(result.scalars())


def _apply_position(learning_session: Session, position: SessionPosition) -> None:
    learning_session.current_topic_id = position.topic_id
    learning_session.current_phase = position.phase
    learning_session.current_step_id = position.step_id
    learning_session.updated_at = datetime.now(UTC)


async def _call_grading(
    client: httpx.AsyncClient,
    settings: SessionsSettings,
    *,
    step: dict[str, object],
    submission: dict[str, object],
) -> GradingCheckResponse:
    try:
        response = await client.post(
            f"{settings.grading_service_url}/internal/v1/grading/check",
            json={"step": step, "submission": submission},
        )
    except httpx.HTTPError as exc:
        raise SessionError(503, "grading unavailable") from exc
    if response.is_error:
        raise SessionError(response.status_code, _upstream_error_detail(response))
    return GradingCheckResponse.model_validate(response.json())


def _upstream_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "grading failed"
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return payload["detail"]
    return "grading failed"


async def _next_attempt_number(
    session: AsyncSession,
    session_id: uuid.UUID,
    topic_id: str,
    phase: str,
    step_id: str,
) -> int:
    result = await session.execute(
        select(func.max(Attempt.attempt_number)).where(
            Attempt.session_id == session_id,
            Attempt.topic_id == topic_id,
            Attempt.phase == phase,
            Attempt.step_id == step_id,
        )
    )
    current = result.scalar_one_or_none()
    return 1 if current is None else current + 1


async def _ensure_assess_attempt_allowed(
    session: AsyncSession,
    learning_session: Session,
    policies: PackPolicies,
) -> None:
    if policies.assess_max_attempts is None:
        return
    result = await session.execute(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.session_id == learning_session.id,
            Attempt.topic_id == learning_session.current_topic_id,
            Attempt.phase == "assess",
            Attempt.step_id == learning_session.current_step_id,
        )
    )
    count = result.scalar_one()
    if count >= policies.assess_max_attempts:
        raise SessionError(409, "assess attempt limit reached")


async def _apply_grading_result(
    session: AsyncSession,
    learning_session: Session,
    grading: GradingCheckResponse,
) -> bool:
    if not grading.passed:
        return False

    progress = await _get_or_create_progress(
        session,
        learning_session.id,
        learning_session.current_topic_id,
    )
    phase = learning_session.current_phase
    if phase == "practice":
        progress.practice_completed = True
    elif phase == "assess":
        progress.assess_completed = True
        best = progress.assess_best_score
        if best is None:
            progress.assess_best_score = grading.score
        else:
            progress.assess_best_score = max(float(best), grading.score)

    if await _session_completed(session, learning_session):
        learning_session.status = "completed"
    return True


async def _session_completed(
    session: AsyncSession,
    learning_session: Session,
) -> bool:
    topics = list_topics(learning_session.manifest)
    result = await session.execute(
        select(PhaseProgress).where(PhaseProgress.session_id == learning_session.id)
    )
    progress_by_topic = {row.topic_id: row for row in result.scalars()}
    return all(
        (progress := progress_by_topic.get(topic.id)) is not None and progress.assess_completed
        for topic in topics
    )


async def _get_or_create_progress(
    session: AsyncSession,
    session_id: uuid.UUID,
    topic_id: str,
) -> PhaseProgress:
    progress = await session.get(PhaseProgress, (session_id, topic_id))
    if progress is None:
        progress = PhaseProgress(session_id=session_id, topic_id=topic_id)
        session.add(progress)
        await session.flush()
    return progress
