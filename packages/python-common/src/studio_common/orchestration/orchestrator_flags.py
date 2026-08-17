from __future__ import annotations

import asyncio
import os

import redis.asyncio as redis

PAUSE_SEARCH_INDEX_KEY = "orchestrator:pause_search_index"
PAUSE_IMPORT_KEY = "orchestrator:pause_import"
ANALYTICS_BATCH_SLEEP_KEY = "orchestrator:analytics_batch_sleep_seconds"


async def orchestrator_flag_enabled(redis_url: str, key: str) -> bool:
    value = await _redis_get(redis_url, key)
    return value == "1"


async def wait_while_orchestrator_paused(
    redis_url: str,
    key: str,
    *,
    interval: float = 5.0,
) -> None:
    while await orchestrator_flag_enabled(redis_url, key):  # noqa: ASYNC110
        await asyncio.sleep(interval)


async def orchestrator_analytics_sleep_seconds(redis_url: str, key: str) -> int:
    value = await _redis_get(redis_url, key)
    if not value:
        return 0
    try:
        return max(int(value), 0)
    except ValueError:
        return 0


def redis_url_from_env() -> str:
    return os.getenv("REDIS_URL", "").strip()


async def _redis_get(redis_url: str, key: str) -> str | None:
    if not redis_url:
        return None
    client = redis.from_url(redis_url, decode_responses=True)
    try:
        raw = await client.get(key)
    finally:
        await client.aclose()
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode()
    return raw
