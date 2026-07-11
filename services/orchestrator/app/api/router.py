from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict
from starlette.responses import Response

router = APIRouter(prefix="/internal/v1/orchestrator", tags=["orchestrator"])
log = structlog.get_logger("orchestrator")


class EditorEventRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    event: Literal["open", "close"]
    language: str
    session_id: str
    user_id: str


@router.post("/editor-events", status_code=status.HTTP_204_NO_CONTENT)
async def editor_events(body: EditorEventRequest) -> Response:
    log.info(
        "editor_event",
        event=body.event,
        language=body.language,
        session_id=body.session_id,
        user_id=body.user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
