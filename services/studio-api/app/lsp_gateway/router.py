from __future__ import annotations

import uuid
from typing import Annotated, Literal

import httpx
import jwt
import structlog
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketException,
    status,
)
from studio_common.jwt_tokens import decode_user_id
from studio_contracts.editor_schemas import lsp_enabled, parse_editor_settings
from studio_contracts.session_schemas import SessionState

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.lsp_gateway.proxy import bridge_lsp

router = APIRouter(tags=["editor"])
log = structlog.get_logger("studio-api.editor")

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]

_SUPPORTED_LSP = frozenset({"pyright", "typescript", "gopls", "sqls"})
EditorEvent = Literal["open", "close"]


class LspTarget:
    __slots__ = ("host", "port")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


def _lsp_target(settings: StudioApiSettings, language: str) -> LspTarget | None:
    match language:
        case "pyright":
            return LspTarget(settings.lsp_pyright_host, settings.lsp_pyright_port)
        case "typescript":
            return LspTarget(settings.lsp_typescript_host, settings.lsp_typescript_port)
        case "gopls":
            return LspTarget(settings.lsp_gopls_host, settings.lsp_gopls_port)
        case "sqls":
            return LspTarget(settings.lsp_sqls_host, settings.lsp_sqls_port)
        case _:
            return None


def _runtime_for_lsp(language: str) -> str | None:
    match language:
        case "pyright":
            return "python"
        case "typescript":
            return "javascript"
        case "gopls":
            return "go"
        case "sqls":
            return "sql"
        case _:
            return None


async def _fetch_session(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> SessionState:
    response = await client.get(
        f"{settings.sessions_service_url}/internal/v1/sessions/{session_id}",
        headers={"X-User-Id": str(user_id)},
    )
    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if response.is_error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="sessions unavailable")
    return SessionState.model_validate(response.json())


async def _fetch_user_settings(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    user_id: uuid.UUID,
) -> dict[str, object]:
    response = await client.get(
        f"{settings.auth_service_url}/internal/v1/auth/me",
        headers={"X-User-Id": str(user_id)},
    )
    if response.is_error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="auth unavailable")
    payload = response.json()
    if not isinstance(payload, dict):
        return {}
    user_settings = payload.get("settings")
    return user_settings if isinstance(user_settings, dict) else {}


async def _authorize_lsp(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    language: str,
) -> None:
    if language not in _SUPPORTED_LSP:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unsupported language")

    runtime = _runtime_for_lsp(language)
    if runtime is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unsupported language")

    session = await _fetch_session(client, settings, user_id, session_id)
    editor_settings = parse_editor_settings(await _fetch_user_settings(client, settings, user_id))
    if not lsp_enabled(
        editor_settings,
        phase=session.current_phase,
        pack_autocomplete=session.policies.assess_autocomplete,
        runtime=runtime,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="autocomplete disabled")


async def _notify_orchestrator(
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


@router.websocket("/v1/lsp/{language}")
async def lsp_socket(
    websocket: WebSocket,
    language: str,
    session_id: Annotated[uuid.UUID, Query()],
) -> None:
    settings: StudioApiSettings = websocket.app.state.settings
    token = websocket.cookies.get(settings.cookie_name)
    if not token:
        raise WebSocketException(code=4401, reason="authentication required")
    try:
        user_id = decode_user_id(token, secret=settings.jwt_secret)
    except (jwt.PyJWTError, ValueError) as exc:
        raise WebSocketException(code=4401, reason="invalid token") from exc

    client: httpx.AsyncClient = websocket.app.state.upstream_client
    try:
        await _authorize_lsp(
            client,
            settings,
            user_id=user_id,
            session_id=session_id,
            language=language,
        )
    except HTTPException as exc:
        raise WebSocketException(code=4403, reason=str(exc.detail)) from exc

    target = _lsp_target(settings, language)
    if target is None:
        raise WebSocketException(code=4404, reason="language server unavailable")

    await websocket.accept()
    try:
        await bridge_lsp(websocket, target.host, target.port)
    except Exception:
        await websocket.close(code=1011)


@router.post("/v1/editor/events", status_code=status.HTTP_204_NO_CONTENT)
async def editor_event(
    event: Annotated[EditorEvent, Query()],
    language: Annotated[str, Query(min_length=1)],
    session_id: Annotated[uuid.UUID, Query()],
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> Response:
    await _notify_orchestrator(
        client,
        settings,
        event=event,
        language=language,
        session_id=session_id,
        user_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
