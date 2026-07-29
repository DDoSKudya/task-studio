from __future__ import annotations

import uuid

from app.infra.models import Attempt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def passed_step_ids(session: AsyncSession, session_id: uuid.UUID) -> set[str]:
    result = await session.execute(
        select(Attempt.step_id)
        .where(
            Attempt.session_id == session_id,
            Attempt.result["passed"].as_boolean().is_(True),
        )
        .distinct()
    )
    return {step_id for step_id in result.scalars()}


async def list_passed_step_ids(session: AsyncSession, session_id: uuid.UUID) -> list[str]:
    return sorted(await passed_step_ids(session, session_id))


async def step_marked_ungradable(
    session: AsyncSession,
    session_id: uuid.UUID,
    step_id: str,
) -> bool:
    result = await session.execute(
        select(Attempt)
        .where(Attempt.session_id == session_id, Attempt.step_id == step_id)
        .order_by(Attempt.created_at.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()
    if attempt is None:
        return False
    payload = attempt.result
    if not isinstance(payload, dict):
        return False
    details = payload.get("details")
    return isinstance(details, dict) and details.get("gradable") is False
