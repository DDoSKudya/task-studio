from __future__ import annotations

import uuid
from collections.abc import Sequence

import httpx
import structlog
from app.config import SessionsSettings
from app.infra.models import AnalyticsOutbox
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.rabbitmq import declare_queue, publish_json, rabbit_connection
from studio_common.system_auth import system_token_headers
from studio_contracts.analytics_schemas import AnalyticsEventMessage

log = structlog.get_logger("sessions.messaging")

_http: httpx.AsyncClient | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def bind_session_factory(factory: async_sessionmaker[AsyncSession] | None) -> None:
    global _session_factory
    _session_factory = factory


def _shared_http() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=10.0)
    return _http


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
            payload = event.model_dump(mode="json")
            await publish_json(
                channel,
                settings.analytics_events_queue,
                payload,
                message_id=str(payload.get("event_id") or uuid.uuid4()),
            )


async def _publish_via_http(
    settings: SessionsSettings,
    events: Sequence[AnalyticsEventMessage],
) -> None:
    if not settings.analytics_service_url:
        return
    response = await _shared_http().post(
        f"{settings.analytics_service_url}/internal/v1/analytics/events",
        json={"events": [event.model_dump(mode="json") for event in events]},
        headers=system_token_headers(),
    )
    response.raise_for_status()


async def _try_channels(
    settings: SessionsSettings,
    events: Sequence[AnalyticsEventMessage],
) -> bool:
    rabbit_enabled = bool(settings.rabbitmq_url)
    http_enabled = bool(settings.analytics_service_url)
    rabbit_ok = False
    http_ok = False

    if rabbit_enabled:
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

    if http_enabled:
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

    if rabbit_ok or http_ok:
        return True

    if http_enabled:
        try:
            await _publish_via_http(settings, events)
            return True
        except Exception as exc:
            log.error(
                "analytics_publish_failed",
                event_count=len(events),
                event_types=[event.event_type for event in events],
                error=str(exc),
                error_type=type(exc).__name__,
            )
    return False


async def _enqueue_outbox(events: Sequence[AnalyticsEventMessage]) -> None:
    if _session_factory is None:
        return
    async with _session_factory() as session:
        for event in events:
            session.add(
                AnalyticsOutbox(
                    id=event.event_id,
                    payload=event.model_dump(mode="json"),
                )
            )
        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            log.warning(
                "analytics_outbox_enqueue_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )


async def flush_analytics_outbox(settings: SessionsSettings, *, limit: int = 50) -> None:
    if _session_factory is None:
        return
    async with _session_factory() as session:
        result = await session.execute(
            select(AnalyticsOutbox).order_by(AnalyticsOutbox.created_at.asc()).limit(limit)
        )
        rows = list(result.scalars())
        if not rows:
            return
        for row in rows:
            try:
                event = AnalyticsEventMessage.model_validate(row.payload)
            except Exception:
                await session.delete(row)
                continue
            if await _try_channels(settings, [event]):
                await session.delete(row)
            else:
                row.attempts += 1
        await session.commit()


async def publish_analytics_events(
    settings: SessionsSettings,
    events: Sequence[AnalyticsEventMessage],
) -> None:
    if not events:
        return

    rabbit_enabled = bool(settings.rabbitmq_url)
    http_enabled = bool(settings.analytics_service_url)
    if not rabbit_enabled and not http_enabled:
        return

    await flush_analytics_outbox(settings)

    if await _try_channels(settings, events):
        return

    await _enqueue_outbox(events)
    raise RuntimeError("analytics publish failed on all channels; queued in outbox")
