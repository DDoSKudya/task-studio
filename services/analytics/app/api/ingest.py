from __future__ import annotations

from app.api.deps import ClickHouseClient, DbSession, Settings
from app.domain.events import process_event
from fastapi import APIRouter
from pydantic import BaseModel, Field
from studio_contracts.analytics_schemas import AnalyticsEventMessage

router = APIRouter(prefix="/internal/v1/analytics", tags=["analytics-ingest"])


class IngestEventsRequest(BaseModel):
    events: list[AnalyticsEventMessage] = Field(default_factory=list)


class IngestEventsResponse(BaseModel):
    accepted: int


@router.post("/events", response_model=IngestEventsResponse)
async def ingest_events(
    body: IngestEventsRequest,
    session: DbSession,
    clickhouse: ClickHouseClient,
    settings: Settings,
) -> IngestEventsResponse:
                                                                       
    accepted = 0
    for event in body.events:
        await process_event(
            session,
            clickhouse,
            settings.clickhouse_database,
            event,
        )
        accepted += 1
    return IngestEventsResponse(accepted=accepted)
