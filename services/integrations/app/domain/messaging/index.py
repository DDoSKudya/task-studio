from __future__ import annotations

import uuid
from collections.abc import Sequence

from aio_pika.abc import AbstractChannel
from app.config import IntegrationsSettings
from app.domain.cache import parse_catalog_course
from studio_common.rabbitmq import declare_queue, publish_json


async def publish_external_courses(
    channel: AbstractChannel,
    settings: IntegrationsSettings,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    courses: Sequence[dict[str, object]],
) -> None:
    await declare_queue(channel, settings.search_index_queue)
    for course in courses:
        parsed = parse_catalog_course(course)
        if parsed is None:
            continue
        await publish_json(
            channel,
            settings.search_index_queue,
            {
                "op": "upsert_external",
                "user_id": str(user_id),
                "platform": platform_id,
                "external_id": parsed["external_id"],
                "title": parsed["title"],
                "description": parsed["description"],
            },
        )
