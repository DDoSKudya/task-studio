from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from app.config import SessionsSettings
from app.domain.common.session_errors import SessionError
from app.domain.integrations.catalog_client import fetch_pack_version
from app.infra.models import PhaseProgress, Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.packs.manifest import first_position


async def create_new_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
    *,
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> Session:
    pack_context = await fetch_pack_version(client, settings, user_id, pack_version_id)
    try:
        position = first_position(pack_context.manifest)
    except ValueError as exc:
        raise SessionError(422, str(exc)) from exc

    now = datetime.now(UTC)
    learning_session = Session(
        user_id=user_id,
        pack_version_id=pack_version_id,
        pack_title=pack_context.pack_title,
        status="active",
        current_topic_id=position.topic_id,
        current_phase=position.phase,
        current_step_id=position.step_id,
        manifest=pack_context.manifest,
        started_at=now,
        updated_at=now,
    )
    session.add(learning_session)
    await session.flush()
    session.add(PhaseProgress(session_id=learning_session.id, topic_id=position.topic_id))
    await session.commit()
    await session.refresh(learning_session)
    return learning_session
