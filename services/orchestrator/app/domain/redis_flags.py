from __future__ import annotations

import redis.asyncio as redis
from app.domain.policies import OrchestratorPolicies
from app.domain.state import ControllerState
from studio_common.orchestrator_flags import (
    ANALYTICS_BATCH_SLEEP_KEY,
    PAUSE_IMPORT_KEY,
    PAUSE_SEARCH_INDEX_KEY,
)

_REDIS_FLAG_TTL_SECONDS = 120


def pause_directives(
    state: ControllerState,
    policies: OrchestratorPolicies,
) -> tuple[bool, bool, int]:
    if state.mode == "power_saving":
        policy = policies.power_saving
        return (
            True,
            not policy.allow_background_import,
            policy.analytics_batch_sleep_seconds,
        )

    if state.mode == "balancing":
        free_ram = state.free_ram_mb
        threshold = policies.balancing.meilisearch_pause_below_ram_mb
        if free_ram is not None and free_ram < threshold:
            return True, False, 0

    return False, False, 0


async def sync_redis_flags(
    redis_client: redis.Redis,
    state: ControllerState,
    policies: OrchestratorPolicies,
) -> None:
    pause_search, pause_import, analytics_sleep = pause_directives(state, policies)

    if pause_search:
        await redis_client.set(PAUSE_SEARCH_INDEX_KEY, "1", ex=_REDIS_FLAG_TTL_SECONDS)
    else:
        await redis_client.delete(PAUSE_SEARCH_INDEX_KEY)

    if pause_import:
        await redis_client.set(PAUSE_IMPORT_KEY, "1", ex=_REDIS_FLAG_TTL_SECONDS)
    else:
        await redis_client.delete(PAUSE_IMPORT_KEY)

    if analytics_sleep > 0:
        await redis_client.set(
            ANALYTICS_BATCH_SLEEP_KEY,
            str(analytics_sleep),
            ex=_REDIS_FLAG_TTL_SECONDS,
        )
    else:
        await redis_client.delete(ANALYTICS_BATCH_SLEEP_KEY)
