from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, WebSocket, status

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.lsp_gateway.access import EditorEvent, notify_orchestrator
from app.lsp_gateway.lsp_socket import run_lsp_socket

router = APIRouter(tags=["editor"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.websocket("/v1/lsp/{language}")
async def lsp_socket(
    websocket: WebSocket,
    language: str,
    session_id: Annotated[uuid.UUID, Query()],
) -> None:
    await run_lsp_socket(websocket, language=language, session_id=session_id)


@router.post("/v1/editor/events", status_code=status.HTTP_204_NO_CONTENT)
async def editor_event(
    event: Annotated[EditorEvent, Query()],
    language: Annotated[str, Query(min_length=1)],
    session_id: Annotated[uuid.UUID, Query()],
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> Response:
    await notify_orchestrator(
        client,
        settings,
        event=event,
        language=language,
        session_id=session_id,
        user_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
