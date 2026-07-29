from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Sequence

from aio_pika.abc import AbstractChannel
from app.config import IntegrationsSettings
from app.domain.messaging.index import publish_external_courses
from studio_common.rabbitmq import declare_queue, publish_json, rabbit_connection


async def _with_channel(
    settings: IntegrationsSettings,
    callback: Callable[[AbstractChannel], Awaitable[None]],
) -> None:
    if not settings.rabbitmq_url:
        return
    async with rabbit_connection(settings.rabbitmq_url) as connection:
        channel = await connection.channel()
        await callback(channel)


async def publish_import_job(
    settings: IntegrationsSettings,
    *,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    platform_id: str,
) -> None:
    async def _publish(channel: AbstractChannel) -> None:
        await declare_queue(channel, settings.import_queue)
        await publish_json(
            channel,
            settings.import_queue,
            {
                "job_id": str(job_id),
                "user_id": str(user_id),
                "platform_id": platform_id,
            },
        )

    await _with_channel(settings, _publish)


async def publish_external_courses_for_index(
    settings: IntegrationsSettings,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    courses: Sequence[dict[str, object]],
) -> None:
    async def _publish(channel: AbstractChannel) -> None:
        await publish_external_courses(
            channel,
            settings,
            user_id=user_id,
            platform_id=platform_id,
            courses=courses,
        )

    await _with_channel(settings, _publish)


async def publish_pack_index(
    channel: AbstractChannel,
    settings: IntegrationsSettings,
    *,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> None:
    await publish_json(
        channel,
        settings.search_index_queue,
        {
            "op": "upsert",
            "user_id": str(user_id),
            "pack_version_id": str(pack_version_id),
        },
    )
