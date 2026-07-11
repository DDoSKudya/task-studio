from __future__ import annotations

from typing import Annotated

from app.api.deps import DbSession
from app.domain.queries import get_attempts_timeline, get_progress, get_skips
from fastapi import APIRouter, Query
from studio_common.internal import InternalUserId
from studio_contracts.analytics_schemas import (
    AttemptsTimelineResponse,
    ProgressResponse,
    SkipsResponse,
)

router = APIRouter(prefix="/internal/v1/analytics", tags=["analytics"])


@router.get("/progress", response_model=ProgressResponse)
async def progress(
    user_id: InternalUserId,
    session: DbSession,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> ProgressResponse:
    return await get_progress(session, user_id, days=days)


@router.get("/skips", response_model=SkipsResponse)
async def skips(user_id: InternalUserId, session: DbSession) -> SkipsResponse:
    return await get_skips(session, user_id)


@router.get("/attempts", response_model=AttemptsTimelineResponse)
async def attempts(
    user_id: InternalUserId,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> AttemptsTimelineResponse:
    return await get_attempts_timeline(session, user_id, limit=limit, cursor=cursor)
