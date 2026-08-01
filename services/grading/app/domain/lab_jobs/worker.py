from __future__ import annotations

import time
import uuid

import httpx
from app.config import GradingSettings
from app.domain.lab import complete_lab_job
from app.domain.lab_jobs.pack import fetch_pack_root, publish_lab_job
from app.domain.llm.grade import try_llm_grade
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "complete_lab_when_pack_unavailable",
    "fetch_pack_root",
    "publish_lab_job",
]


async def complete_lab_when_pack_unavailable(
    session: AsyncSession,
    settings: GradingSettings,
    client: httpx.AsyncClient,
    *,
    attempt_id: uuid.UUID,
    user_id: uuid.UUID,
    step: dict[str, object],
) -> None:
    instructions = step.get("instructions")
    submission: dict[str, object] = {
        "text": (
            instructions[:500]
            if isinstance(instructions, str) and instructions.strip()
            else "Lab runner could not start; no learner report attached."
        )
    }
    outcome = await try_llm_grade(
        client,
        settings,
        step=step,
        submission=submission,
        kind="lab",
        user_id=user_id,
        started=time.perf_counter(),
        prior_feedback="lab pack unavailable",
        prior_checker="lab",
    )
    if outcome is None:
        await complete_lab_job(
            session,
            settings,
            client,
            attempt_id=attempt_id,
            passed=False,
            score=0.0,
            feedback="Lab is unavailable and AI grading failed",
            details={"status": "completed", "gradable": False, "checker": "lab"},
            duration_ms=0,
        )
        return
    await complete_lab_job(
        session,
        settings,
        client,
        attempt_id=attempt_id,
        passed=outcome.passed,
        score=outcome.score,
        feedback=outcome.feedback,
        details={**outcome.details, "status": "completed"},
        duration_ms=outcome.duration_ms,
    )
