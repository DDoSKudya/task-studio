\
\
\
\
\
\
   

from __future__ import annotations

import uuid

import httpx
from app.config import GradingSettings
from app.domain.check.cascade import GradeContext, run_chain, stage_llm, stage_ungradable
from app.domain.code.stages import (
    stage_local_harness,
    stage_require_source,
    stage_stepik,
)
from app.domain.check.outcome import CheckOutcome
from app.domain.piston.client import execute_piston_job, piston_outcome
from app.domain.sql.grade import stage_sql_local
from app.domain.stepik_quiz import (
    StepikQuizError,
    fetch_stepik_credentials,
    grade_code_via_stepik,
)

                                                                      
__all__ = [
    "grade_code",
    "StepikQuizError",
    "fetch_stepik_credentials",
    "grade_code_via_stepik",
    "execute_piston_job",
    "piston_outcome",
]


async def grade_code(
    step: dict[str, object],
    submission: dict[str, object],
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
    user_id: uuid.UUID | None = None,
) -> CheckOutcome:
    ctx = GradeContext(
        step=step,
        submission=submission,
        settings=settings,
        client=client,
        kind="code",
        user_id=user_id,
        prior_feedback="no automated tests",
        prior_checker="none",
        ungradable_feedback="This step has no automated tests for code grading",
    )
    return await run_chain(
        ctx,
        (
            stage_require_source,
            stage_stepik,
            stage_sql_local,
            stage_local_harness,
            stage_llm,
            stage_ungradable,
        ),
    )
