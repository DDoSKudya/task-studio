from __future__ import annotations

import uuid

from app.api.deps import ClientDep, ConfigDep, RedisDep, UserId
from app.domain.chat import build_hints
from app.domain.grade import grade_submission
from app.domain.warmup import warmup_cursor_for_session
from fastapi import APIRouter
from studio_contracts.tutor_schemas import (
    TutorGradeRequest,
    TutorGradeResponse,
    TutorHintResponse,
    TutorWarmupRequest,
    TutorWarmupResponse,
)

router = APIRouter()


@router.get("/hints/{step_id}", response_model=TutorHintResponse)
async def get_hints(
    step_id: str,
    session_id: uuid.UUID,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
    redis: RedisDep,
) -> TutorHintResponse:
    return await build_hints(
        client,
        redis,
        config,
        user_id=user_id,
        session_id=session_id,
        step_id=step_id,
    )


@router.post("/grade", response_model=TutorGradeResponse)
async def tutor_grade(
    body: TutorGradeRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> TutorGradeResponse:
    return await grade_submission(
        client,
        config,
        user_id=user_id,
        body=body,
    )


@router.post("/warmup", response_model=TutorWarmupResponse)
async def tutor_warmup(
    body: TutorWarmupRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
    redis: RedisDep,
) -> TutorWarmupResponse:
    return await warmup_cursor_for_session(
        client,
        redis,
        config,
        user_id=user_id,
        session_id=body.session_id,
    )
