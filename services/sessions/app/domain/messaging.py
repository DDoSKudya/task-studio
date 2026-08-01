from __future__ import annotations

from collections.abc import Sequence

import httpx
import structlog
from app.config import SessionsSettings
from studio_common.rabbitmq import declare_queue, publish_json, rabbit_connection
from studio_contracts.analytics_schemas import AnalyticsEventMessage

log = structlog.get_logger("sessions.messaging")


async def _publish_via_rabbit(
    settings: SessionsSettings,
    events: Sequence[AnalyticsEventMessage],
) -> None:
    if not settings.rabbitmq_url:
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


async def _publish_via_http(
    settings: SessionsSettings,
    events: Sequence[AnalyticsEventMessage],
) -> None:
    if not settings.analytics_service_url:
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{settings.analytics_service_url}/internal/v1/analytics/events",
            json={"events": [event.model_dump(mode="json") for event in events]},
        )
        response.raise_for_status()


async def publish_analytics_events(
    settings: SessionsSettings,
    events: Sequence[AnalyticsEventMessage],
) -> None:
    if not events:
        return

    rabbit_ok = False
    http_ok = False

    try:
        await _publish_via_rabbit(settings, events)
        rabbit_ok = True
    except Exception as exc:
        log.warning(
            "analytics_publish_rabbit_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            event_count=len(events),
        )

    try:
        await _publish_via_http(settings, events)
        http_ok = True
    except Exception as exc:
        log.warning(
            "analytics_publish_http_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            event_count=len(events),
        )

    if not rabbit_ok and not http_ok:
        log.error(
            "analytics_publish_failed",
            event_count=len(events),
            event_types=[event.event_type for event in events],
        )
