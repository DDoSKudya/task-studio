from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bound_contextvars


async def inject_request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    raw_request_id = request.headers.get("X-Request-Id")
    request_id = (raw_request_id or "").strip() or str(uuid.uuid4())
    with bound_contextvars(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


def register_request_id_middleware(app: FastAPI) -> None:
    _ = app.middleware("http")(inject_request_id)
