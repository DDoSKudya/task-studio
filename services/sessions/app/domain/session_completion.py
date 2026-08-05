from __future__ import annotations

from app.infra.models import PhaseProgress, Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.manifest import get_step, list_topics, phase_step_ids, read_policies


async def topic_practice_passed(
    session: AsyncSession,
    learning_session: Session,
    *,
    topic_id: str | None = None,
) -> bool:
    resolved_topic = topic_id or learning_session.current_topic_id
    required = [
        step_id
        for step_id in phase_step_ids(
            learning_session.manifest,
            resolved_topic,
            "practice",
        )
        if get_step(learning_session.manifest, step_id).get("kind")
        in {
            "quiz",
            "code",
            "lab",
            "task",
        }
    ]
    if not required:
        return True
    from app.domain.session_passed import passed_step_ids

    passed = await passed_step_ids(session, learning_session.id)
    return all(step_id in passed for step_id in required)


async def topic_assess_passed(
    session: AsyncSession,
    learning_session: Session,
    *,
    topic_id: str | None = None,
) -> bool:
    resolved_topic = topic_id or learning_session.current_topic_id
    required = list(
        phase_step_ids(
            learning_session.manifest,
            resolved_topic,
            "assess",
        )
    )
    if not required:
        return True
    from app.domain.session_passed import passed_step_ids

    passed = await passed_step_ids(session, learning_session.id)
    return all(step_id in passed for step_id in required)


async def session_completed(
    session: AsyncSession,
    learning_session: Session,
) -> bool:
    topics = list_topics(learning_session.manifest)
    order = read_policies(learning_session.manifest).phase_order
    result = await session.execute(
        select(PhaseProgress).where(PhaseProgress.session_id == learning_session.id)
    )
    progress_by_topic = {row.topic_id: row for row in result.scalars()}
    for topic in topics:
        progress = progress_by_topic.get(topic.id)
        if progress is None:
            return False
        for phase in order:
            if phase == "study" and not (progress.study_completed or progress.study_skipped):
                return False
            if phase == "practice" and not progress.practice_completed:
                return False
            if phase == "assess" and not progress.assess_completed:
                return False
    return True
