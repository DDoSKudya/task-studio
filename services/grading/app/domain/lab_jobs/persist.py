from __future__ import annotations

import uuid

from app.infra.models import GradingResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_lab_result(session: AsyncSession, attempt_id: uuid.UUID) -> GradingResult | None:
    row = await session.execute(select(GradingResult).where(GradingResult.attempt_id == attempt_id))
    return row.scalar_one_or_none()


async def persist_lab_result(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    passed: bool,
    score: float,
    details: dict[str, object],
    duration_ms: int,
) -> None:
    row = await get_lab_result(session, attempt_id)
    if row is None:
        session.add(
            GradingResult(
                attempt_id=attempt_id,
                checker="lab",
                passed=passed,
                score=score,
                details=details,
                duration_ms=duration_ms,
            )
        )
    else:
        row.passed = passed
        row.score = score
        row.duration_ms = duration_ms
        row.details = details
    await session.commit()


def result_details(
    details: dict[str, object],
    *,
    feedback: str | None,
    status: str,
) -> dict[str, object]:
    merged = {**details, "status": status}
    if feedback:
        merged["feedback"] = feedback
    return merged
