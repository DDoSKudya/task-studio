from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import redis.asyncio as redis
import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.router import router as orchestrator_router
from app.config import load_settings
from app.domain.docker import DockerControl, docker_client
from app.domain.policies import load_policies
from app.domain.state import ControllerState
from app.worker import start_control_loop


def build_app() -> FastAPI:
    configure_logging("orchestrator")
    log = structlog.get_logger("orchestrator")
    settings = load_settings()
    policies_path = Path(settings.policies_path)
    if not policies_path.is_file():
        msg = f"policies file not found: {policies_path}"
        raise RuntimeError(msg)
    policies = load_policies(policies_path)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        app.state.managed_service_names = frozenset(policies.managed_services.all_names())
        app.state.controller_state = ControllerState(mode=settings.mode)
        loop_task: asyncio.Task[None] | None = None
        redis_client: redis.Redis | None = None
        if settings.redis_url:
            redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        async with docker_client(settings.docker_socket) as docker_http:
            docker = DockerControl(docker_http, compose_project=settings.compose_project)
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                loop_task = start_control_loop(
                    settings,
                    policies,
                    app.state.controller_state,
                    docker,
                    http_client,
                    redis_client=redis_client,
                )
                log.info("service_started", mode=settings.mode)
                try:
                    yield
                finally:
                    if loop_task is not None:
                        loop_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await loop_task
                    if redis_client is not None:
                        await redis_client.aclose()
                    log.info("service_stopped")

    app = FastAPI(title="orchestrator", lifespan=lifespan)
    register_request_id_middleware(app)
    configure_otel("orchestrator", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(orchestrator_router)
    return app


app = build_app()
