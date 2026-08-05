from __future__ import annotations

import asyncio

import structlog
from app.domain.aggregates import update_postgres_aggregates
from app.infra.clickhouse import insert_event
from app.infra.models import ProcessedEvent
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import ClickHouseError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.analytics_schemas import AnalyticsEventMessage

log = structlog.get_logger("analytics.events")


class PermanentEventError(Exception):
    pass


def parse_event_message(payload: dict[str, object]) -> AnalyticsEventMessage:
    try:
        return AnalyticsEventMessage.model_validate(payload)
    except ValidationError as exc:
        raise PermanentEventError("invalid event payload") from exc


async def process_event(
    session: AsyncSession,
    client: Client | None,
    database: str,
    event: AnalyticsEventMessage,
) -> None:
    if await session.get(ProcessedEvent, event.event_id) is not None:
        return

    if client is not None:
        try:
            await asyncio.to_thread(insert_event, client, database, event)
        except (ClickHouseError, OSError, ConnectionError, TimeoutError) as exc:
            log.warning(
                "clickhouse_insert_failed",
                event_id=str(event.event_id),
                error=str(exc),
            )
            raise

    await update_postgres_aggregates(session, event)
    session.add(ProcessedEvent(event_id=event.event_id))
    await session.commit()
    log.info(
        "analytics_event_stored",
        event_id=str(event.event_id),
        event_type=event.event_type,
        user_id=str(event.user_id),
    )
