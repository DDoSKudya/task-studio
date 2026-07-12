from __future__ import annotations

import asyncio

import structlog
from aio_pika.abc import AbstractIncomingMessage
from clickhouse_connect.driver.client import Client
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.orchestrator_flags import (
    ANALYTICS_BATCH_SLEEP_KEY,
    orchestrator_analytics_sleep_seconds,
    redis_url_from_env,
)
from studio_common.rabbitmq import consume_json, declare_dlq, declare_queue, rabbit_connection

from app.config import AnalyticsSettings
from app.domain.events import parse_event_message, process_event

log = structlog.get_logger("analytics.worker")


def start_events_worker(
    settings: AnalyticsSettings,
    session_factory: async_sessionmaker[AsyncSession],
    client: Client,
) -> asyncio.Task[None] | None:
    if not settings.rabbitmq_url:
        log.warning("rabbitmq_disabled")
        return None

    async def _runner() -> None:
        async with rabbit_connection(settings.rabbitmq_url) as connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=10)
            queue = await declare_queue(channel, settings.analytics_events_queue)
            dlq = await declare_dlq(channel, settings.analytics_events_queue)

            async def handle(payload: dict[str, object], _message: AbstractIncomingMessage) -> None:
                sleep_seconds = await orchestrator_analytics_sleep_seconds(
                    redis_url_from_env(),
                    ANALYTICS_BATCH_SLEEP_KEY,
                )
                if sleep_seconds:
                    await asyncio.sleep(sleep_seconds)
                event = parse_event_message(payload)
                async with session_factory() as session:
                    await process_event(
                        session,
                        client,
                        settings.clickhouse_database,
                        event,
                    )

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())
