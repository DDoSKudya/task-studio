from __future__ import annotations

import uuid
from collections import defaultdict
from typing import cast

from app.infra.models import PhaseProgress, Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.session_schemas import PackProgressItem, SessionStatus
from studio_contracts.packs.manifest import PhaseName


def chapter_title_from_manifest(manifest: dict[str, object], topic_id: str) -> str:
    raw_topics = manifest.get("topics")
    if isinstance(raw_topics, list):
        for item in raw_topics:
            if not isinstance(item, dict):
                continue
            if item.get("id") != topic_id:
                continue
            title = item.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
    return topic_id


def _phase_weight(row: PhaseProgress) -> int:
    if row.assess_completed:
        return 3
    if row.practice_completed:
        return 2
    if row.study_completed or row.study_skipped:
        return 1
    return 0


def progress_percent_from_rows(rows: list[PhaseProgress]) -> int:
    if not rows:
        return 0
    done = sum(_phase_weight(row) for row in rows)
    return round((done / (len(rows) * 3)) * 100)


async def list_pack_progress(session: AsyncSession, user_id: uuid.UUID) -> list[PackProgressItem]:
    result = await session.execute(
        select(Session).where(Session.user_id == user_id).order_by(Session.updated_at.desc())
    )
    learning_sessions = list(result.scalars())
    if not learning_sessions:
        return []

    session_ids = [row.id for row in learning_sessions]
    progress_result = await session.execute(
        select(PhaseProgress).where(PhaseProgress.session_id.in_(session_ids))
    )
    by_session: dict[uuid.UUID, list[PhaseProgress]] = defaultdict(list)
    for row in progress_result.scalars():
        by_session[row.session_id].append(row)

    items: list[PackProgressItem] = []
    for learning_session in learning_sessions:
        rows = by_session.get(learning_session.id, [])
        items.append(
            PackProgressItem(
                id=learning_session.id,
                pack_version_id=learning_session.pack_version_id,
                pack_title=learning_session.pack_title,
                status=cast(SessionStatus, learning_session.status),
                current_topic_id=learning_session.current_topic_id,
                current_phase=cast(PhaseName, learning_session.current_phase),
                current_step_id=learning_session.current_step_id,
                started_at=learning_session.started_at,
                updated_at=learning_session.updated_at,
                chapter_title=chapter_title_from_manifest(
                    learning_session.manifest,
                    learning_session.current_topic_id,
                ),
                progress_percent=progress_percent_from_rows(rows),
            )
        )
    return items
