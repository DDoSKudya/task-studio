from __future__ import annotations

import uuid

import httpx
from app.config import TutorConfig
from app.domain.errors import TutorError
from fastapi import status
from redis.asyncio import Redis
from studio_contracts.api.session_schemas import CourseDigest

_CACHE_TTL_SECONDS = 60 * 60 * 6
_DIGEST_UNAVAILABLE = "course digest unavailable"


async def fetch_course_digest(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> CourseDigest:
    response = await client.get(
        f"{config.sessions_service_url}/internal/v1/sessions/{session_id}/course-digest",
        headers={"X-User-Id": str(user_id)},
    )
    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise TutorError(status.HTTP_404_NOT_FOUND, "session not found")
    if response.is_error:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, _DIGEST_UNAVAILABLE)
    return CourseDigest.model_validate(response.json())


async def get_cached_course_digest(
    client: httpx.AsyncClient,
    redis: Redis,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> CourseDigest:
    cache_key = f"tutor:course-digest:{pack_version_id}"
    cached = await redis.get(cache_key)
    if isinstance(cached, bytes | str):
        raw = cached.decode("utf-8") if isinstance(cached, bytes) else cached
        try:
            return CourseDigest.model_validate_json(raw)
        except ValueError:
            pass

    digest = await fetch_course_digest(
        client,
        config,
        user_id=user_id,
        session_id=session_id,
    )
    await redis.set(cache_key, digest.model_dump_json(), ex=_CACHE_TTL_SECONDS)
    return digest
