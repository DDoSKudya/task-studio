from __future__ import annotations

from collections.abc import Sequence

from app.config import SessionsSettings
from studio_common.rabbitmq import declare_queue, publish_json, rabbit_connection
from studio_contracts.analytics_schemas import AnalyticsEventMessage


async def publish_analytics_events(
    settings: SessionsSettings,
    events: Sequence[AnalyticsEventMessage],
) -> None:
    if not events or not settings.rabbitmq_url:
        return

    async with rabbit_connection(settings.rabbitmq_url) as connection:
        channel = await connection.channel()
        await declare_queue(channel, settings.analytics_events_queue)
        for event in events:
            await publish_json(
                channel,
                settings.analytics_events_queue,
                event.model_dump(mode="json"),
            )
