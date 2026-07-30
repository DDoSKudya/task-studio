from __future__ import annotations

from typing import Any

import httpx


async def _stage_json(
    client: httpx.AsyncClient,
    target: object,
    *,
    compact: bool,
    stage: str,
    user_message: str,
    max_tokens: int,
) -> dict[str, Any]:

    from app.domain import course_from_article

    return await course_from_article._stage_json(
        client,
        target,
        compact=compact,
        stage=stage,
        user_message=user_message,
        max_tokens=max_tokens,
    )
