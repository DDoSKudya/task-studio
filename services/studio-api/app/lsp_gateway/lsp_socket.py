from __future__ import annotations

import asyncio
import uuid

import httpx
import jwt
from fastapi import HTTPException, WebSocket, WebSocketException
from starlette.websockets import WebSocketDisconnect
from studio_common.security.jwt_tokens import decode_user_id

from app.config import StudioApiSettings
from app.lsp_gateway.access import authorize_lsp
from app.lsp_gateway.proxy import bridge_lsp
from app.lsp_gateway.targets import lsp_target


async def run_lsp_socket(
    websocket: WebSocket,
    *,
    language: str,
    session_id: uuid.UUID,
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
        await authorize_lsp(
            client,
            settings,
            user_id=user_id,
            session_id=session_id,
            language=language,
        )
    except HTTPException as exc:
        raise WebSocketException(code=4403, reason=str(exc.detail)) from exc

    target = lsp_target(settings, language)
    if target is None:
        raise WebSocketException(code=4404, reason="language server unavailable")

    await websocket.accept()
    try:
        await bridge_lsp(websocket, target.host, target.port)
    except asyncio.CancelledError:
        raise
    except (ConnectionError, OSError, TimeoutError, WebSocketDisconnect, BrokenPipeError):
        await websocket.close(code=1011)
