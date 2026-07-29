from __future__ import annotations

import uuid

from app.api.check_route import run_and_store_check
from app.api.deps import DbSession, GradingHttpClient, Settings
from app.domain.check import parse_attempt_id
from app.domain.lab import complete_lab_job, enqueue_lab_job
from fastapi import APIRouter
from studio_contracts.grading_schemas import (
    GradingCheckRequest,
    GradingCheckResponse,
    GradingLabCompleteRequest,
    GradingLabSubmitRequest,
    GradingLabSubmitResponse,
)

router = APIRouter(prefix="/internal/v1/grading", tags=["grading"])


@router.post("/check", response_model=GradingCheckResponse)
async def grade_submission(
    body: GradingCheckRequest,
    session: DbSession,
    settings: Settings,
    client: GradingHttpClient,
) -> GradingCheckResponse:
    return await run_and_store_check(session, body, settings=settings, client=client)


@router.post("/lab", response_model=GradingLabSubmitResponse)
async def submit_lab(
    body: GradingLabSubmitRequest,
    session: DbSession,
    settings: Settings,
) -> GradingLabSubmitResponse:
    attempt_id = parse_attempt_id(body.submission)
    return await enqueue_lab_job(
        session,
        settings,
        attempt_id=attempt_id,
        user_id=uuid.UUID(body.user_id),
        pack_version_id=uuid.UUID(body.pack_version_id),
        step=body.step,
    )


@router.post("/lab/complete")
async def complete_lab(
    body: GradingLabCompleteRequest,
    session: DbSession,
    settings: Settings,
    client: GradingHttpClient,
) -> dict[str, str]:
    attempt_id = parse_attempt_id({"attempt_id": body.attempt_id})
    await complete_lab_job(
        session,
        settings,
        client,
        attempt_id=attempt_id,
        passed=body.passed,
        score=body.score,
        feedback=body.feedback,
        details=body.details,
        duration_ms=body.duration_ms,
    )
    return {"status": "ok"}
