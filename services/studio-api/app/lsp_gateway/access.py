from __future__ import annotations

import uuid
from typing import Literal

import httpx
import structlog
from fastapi import HTTPException, status
from studio_contracts.api.editor_schemas import lsp_enabled, parse_editor_settings

from app.config import StudioApiSettings
from app.lsp_gateway.access_fetch import fetch_session, fetch_user_settings
from app.lsp_gateway.targets import SUPPORTED_LSP, runtime_for_lsp

log = structlog.get_logger("studio-api.editor")

EditorEvent = Literal["open", "close"]

__all__ = [
    "EditorEvent",
    "authorize_lsp",
    "fetch_session",
    "fetch_user_settings",
    "notify_orchestrator",
]


async def authorize_lsp(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    language: str,
) -> None:
    if language not in SUPPORTED_LSP:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unsupported language")

    runtime = runtime_for_lsp(language)
    if runtime is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unsupported language")

    session = await fetch_session(client, settings, user_id, session_id)
    editor_settings = parse_editor_settings(await fetch_user_settings(client, settings, user_id))
    if not lsp_enabled(
        editor_settings,
        phase=session.current_phase,
        pack_autocomplete=session.policies.assess_autocomplete,
        runtime=runtime,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="autocomplete disabled")


async def notify_orchestrator(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    *,
    event: EditorEvent,
    language: str,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    try:
        response = await client.post(
            f"{settings.orchestrator_service_url}/internal/v1/orchestrator/editor-events",
            json={
                "event": event,
                "language": language,
                "session_id": str(session_id),
                "user_id": str(user_id),
            },
            timeout=2.0,
        )
    except httpx.HTTPError as exc:
        log.warning("orchestrator_editor_event_failed", error=str(exc))
        return
    if response.is_error:
        log.warning("orchestrator_editor_event_rejected", status_code=response.status_code)
