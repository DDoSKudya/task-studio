from __future__ import annotations

import asyncio
import uuid

import httpx
from app.config import TutorConfig
from app.domain.chat.session.models import TutorView
from app.domain.context import fetch_session, fetch_step, fetch_user_settings
from app.domain.course.cache import get_cached_course_digest
from app.domain.errors import TutorError
from fastapi import status
from redis.asyncio import Redis
from studio_contracts.api.session_schemas import SessionState
from studio_contracts.api.tutor_schemas import TutorSettings, tutor_allowed


async def load_tutor_view(
    client: httpx.AsyncClient,
    redis: Redis,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> TutorView:
    session, user_settings, step = await asyncio.gather(
        fetch_session(client, config, user_id=user_id, session_id=session_id),
        fetch_user_settings(client, config, user_id),
        fetch_step(client, config, user_id=user_id, session_id=session_id),
    )
    _ensure_tutor_allowed(session, user_settings)
    digest = await get_cached_course_digest(
        client,
        redis,
        config,
        user_id=user_id,
        session_id=session_id,
        pack_version_id=session.pack_version_id,
    )
    return TutorView(session=session, step=step, user_settings=user_settings, digest=digest)


def _ensure_tutor_allowed(session: SessionState, user_settings: TutorSettings) -> None:
    if not tutor_allowed(
        session.current_phase,
        pack_tutor_enabled=session.policies.tutor_enabled,
        user_enabled=user_settings.enabled,
    ):
        raise TutorError(status.HTTP_403_FORBIDDEN, "tutor disabled")
