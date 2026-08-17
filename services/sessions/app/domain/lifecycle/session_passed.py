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
