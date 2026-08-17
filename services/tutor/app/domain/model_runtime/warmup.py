from __future__ import annotations

import uuid

import httpx
from app.config import TutorConfig
from redis.asyncio import Redis
from studio_contracts.api.tutor_schemas import TutorWarmupResponse


def is_cursor_provider(provider_url: str | None) -> bool:
    if not provider_url:
        return False
    from app.domain.llm.target import LlmTarget, is_cursor_target

    return is_cursor_target(LlmTarget(provider_url.rstrip("/"), None, "auto"))


async def warmup_cursor_for_session(
    client: httpx.AsyncClient,
    redis: Redis,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> TutorWarmupResponse:
    _ = (client, redis, config, user_id, session_id)

    return TutorWarmupResponse(ok=True, skipped=True, detail="cursor warmup disabled")
