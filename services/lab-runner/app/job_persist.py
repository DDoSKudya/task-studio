from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.runner import LabRunOutcome
from app.infra.models import LabRun


async def mark_running(
    session_factory: async_sessionmaker[AsyncSession],
    lab_run_id: uuid.UUID,
    attempt_id: uuid.UUID,
    pack_root: str,
    step: dict[str, object],
) -> bool:
    async with session_factory() as session:
        existing = await session.get(LabRun, lab_run_id)
        if existing is not None and existing.status == "completed":
            return False
        if existing is None:
            session.add(
                LabRun(
                    id=lab_run_id,
                    attempt_id=attempt_id,
                    status="running",
                    pack_root=pack_root,
                    step=step,
                )
            )
        else:
            existing.status = "running"
        await session.commit()
    return True


async def store_outcome(
    session_factory: async_sessionmaker[AsyncSession],
    lab_run_id: uuid.UUID,
    outcome: LabRunOutcome,
) -> None:
    async with session_factory() as session:
        row = await session.get(LabRun, lab_run_id)
        if row is None:
            return
        row.status = "completed"
        row.finished_at = datetime.now(UTC)
        row.result = asdict(outcome)
        await session.commit()
