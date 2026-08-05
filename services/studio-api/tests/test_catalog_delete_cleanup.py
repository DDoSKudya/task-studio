from __future__ import annotations

import importlib.util
import sys
import types
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class Request:  # minimal placeholder for `from fastapi import Request`
        pass

    class FastAPI:
        def __init__(self, *_args, **_kwargs) -> None:
            self.state = SimpleNamespace()

    class _Status:
        HTTP_502_BAD_GATEWAY = 502

    fastapi_stub = types.ModuleType("fastapi")
    fastapi_stub.__dict__["HTTPException"] = HTTPException
    fastapi_stub.__dict__["Request"] = Request
    fastapi_stub.__dict__["FastAPI"] = FastAPI
    fastapi_stub.__dict__["status"] = _Status
    sys.modules["fastapi"] = fastapi_stub

try:
    import structlog  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    structlog_stub = types.ModuleType("structlog")

    class _Logger:
        def info(self, *_args, **_kwargs) -> None:
            return None

        def warning(self, *_args, **_kwargs) -> None:
            return None

    def _get_logger(*_args, **_kwargs) -> _Logger:
        return _Logger()

    structlog_stub.__dict__["get_logger"] = _get_logger
    sys.modules["structlog"] = structlog_stub


try:
    import prometheus_fastapi_instrumentator  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    prometheus_stub = types.ModuleType("prometheus_fastapi_instrumentator")

    class Instrumentator:
        def instrument(self, *_args, **_kwargs) -> Instrumentator:
            return self

        def expose(self, *_args, **_kwargs) -> None:
            return None

    prometheus_stub.__dict__["Instrumentator"] = Instrumentator
    sys.modules["prometheus_fastapi_instrumentator"] = prometheus_stub


def _load_delete_module():
    service_root = Path(__file__).resolve().parents[1]
    if str(service_root) not in sys.path:
        sys.path.insert(0, str(service_root))

    module_path = service_root / "app" / "api" / "catalog_routes" / "delete.py"
    spec = importlib.util.spec_from_file_location("studio_api_catalog_delete_test", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


delete_module = _load_delete_module()
delete_pack_with_cleanup = delete_module.delete_pack_with_cleanup


@pytest.mark.asyncio
async def test_delete_pack_cleanup_failure_does_not_block_catalog_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pack_id = uuid.uuid4()
    user_id = uuid.uuid4()
    version_id = uuid.uuid4()

    pack = SimpleNamespace(versions=[SimpleNamespace(id=version_id)])

    def parse_upstream_mock(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return pack

    monkeypatch.setattr(delete_module, "parse_upstream", parse_upstream_mock)

    request = httpx.Request("GET", "http://test")
    call_service_mock = AsyncMock(
        side_effect=[
            httpx.Response(
                200,
                content=b"{}",
                headers={"Content-Type": "application/json"},
                request=request,
            ),  # get pack detail
            httpx.Response(
                500,
                content=b'{"detail":"sessions unavailable"}',
                headers={"Content-Type": "application/json"},
                request=request,
            ),
            httpx.Response(
                500,
                content=b'{"detail":"search unavailable"}',
                headers={"Content-Type": "application/json"},
                request=request,
            ),
            httpx.Response(204, request=request),  # delete pack
        ],
    )
    monkeypatch.setattr(delete_module, "call_service", call_service_mock)

    client = AsyncMock(spec=httpx.AsyncClient)
    settings = SimpleNamespace(
        catalog_service_url="http://catalog",
        sessions_service_url="http://sessions",
        search_service_url="http://search",
    )

    await delete_pack_with_cleanup(client, settings, user_id=user_id, pack_id=pack_id)

    assert call_service_mock.call_count == 4
    assert call_service_mock.call_args_list[-1].args[2] == "delete"
