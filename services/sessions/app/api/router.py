from __future__ import annotations

from app.api.deps import DbSession, Settings, UpstreamClient
from app.api.mappers import session_summary
from app.api.routes.attempts import router as attempts_router
from app.api.routes.lifecycle import router as lifecycle_router
from app.api.routes.study import router as study_router
from app.api.session_views import build_session_state
from app.domain.analytics_events import analytics_event
from app.domain.messaging import publish_analytics_events
from app.domain.sessions import (
    abandon_sessions_for_pack_versions,
    list_sessions,
    start_session,
)
from fastapi import APIRouter
from studio_common.internal import InternalUserId
from studio_contracts.session_schemas import (
    AbandonSessionsRequest,
    SessionState,
    SessionSummary,
    StartSessionRequest,
)

router = APIRouter(prefix="/internal/v1/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionSummary])
async def list_user_sessions(user_id: InternalUserId, session: DbSession) -> list[SessionSummary]:
    rows = await list_sessions(session, user_id)
    return [session_summary(row) for row in rows]


@router.post("/abandon-by-pack-versions")
async def abandon_by_pack_versions(
    body: AbandonSessionsRequest,
    user_id: InternalUserId,
    session: DbSession,
) -> dict[str, int]:
    count = await abandon_sessions_for_pack_versions(
        session,
        user_id,
        body.pack_version_ids,
        pack_titles=body.pack_titles,
    )
    return {"abandoned": count}


@router.post("", response_model=SessionState)
async def create_session(
    body: StartSessionRequest,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    client: UpstreamClient,
) -> SessionState:
    learning_session, created = await start_session(
        session,
        user_id,
        body.pack_version_id,
        settings=settings,
        client=client,
    )
    if created:
        await publish_analytics_events(
            settings,
            [analytics_event(learning_session, "session_started")],
        )
    return await build_session_state(session, learning_session)


router.include_router(lifecycle_router)
router.include_router(study_router)
router.include_router(attempts_router)
