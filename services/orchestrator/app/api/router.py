from __future__ import annotations

from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from starlette.responses import Response
from studio_contracts.orchestrator_schemas import (
    ManagedServiceStatus,
    OrchestratorMode,
    OrchestratorModeRequest,
    OrchestratorStatusResponse,
)

from app.config import OrchestratorSettings
from app.domain.state import ControllerState

router = APIRouter(prefix="/internal/v1/orchestrator", tags=["orchestrator"])
log = structlog.get_logger("orchestrator")


class EditorEventRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    event: Literal["open", "close"]
    language: str
    session_id: str
    user_id: str


def get_settings(request: Request) -> OrchestratorSettings:
    settings: OrchestratorSettings | None = getattr(request.app.state, "settings", None)
    if settings is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")
    return settings


def get_state(request: Request) -> ControllerState:
    state: ControllerState | None = getattr(request.app.state, "controller_state", None)
    if state is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")
    return state


def get_managed_service_names(request: Request) -> frozenset[str]:
    names: frozenset[str] | None = getattr(request.app.state, "managed_service_names", None)
    if names is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")
    return names


def verify_system_token(
    settings: Annotated[OrchestratorSettings, Depends(get_settings)],
    x_system_token: Annotated[str | None, Header(alias="X-System-Token")] = None,
) -> None:
    if settings.system_token and x_system_token != settings.system_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid system token")


type State = Annotated[ControllerState, Depends(get_state)]
type SystemAuth = Annotated[None, Depends(verify_system_token)]
type ManagedNames = Annotated[frozenset[str], Depends(get_managed_service_names)]


@router.get("/status", response_model=OrchestratorStatusResponse)
async def orchestrator_status(
    _auth: SystemAuth,
    state: State,
    managed_names: ManagedNames,
) -> OrchestratorStatusResponse:
    managed = [
        ManagedServiceStatus(
            service=service,
            running=running,
            desired=_desired_state(state.mode, service, managed_names),
        )
        for service, running in sorted(state.managed_running.items())
    ]
    return OrchestratorStatusResponse(
        mode=state.mode,
        free_ram_mb=state.free_ram_mb,
        load_average=state.load_average,
        all_users_external_llm=state.all_users_external_llm,
        grading_cpu_hot=state.grading_cpu_hot,
        managed_services=managed,
        warnings=state.warnings,
    )


@router.get("/mode")
async def get_mode(_auth: SystemAuth, state: State) -> dict[str, OrchestratorMode]:
    return {"mode": state.mode}


@router.put("/mode", status_code=status.HTTP_204_NO_CONTENT)
async def set_mode(
    body: OrchestratorModeRequest,
    _auth: SystemAuth,
    state: State,
) -> Response:
    state.mode = body.mode
    log.info("orchestrator_mode_changed", mode=body.mode)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/editor-events", status_code=status.HTTP_204_NO_CONTENT)
async def editor_events(body: EditorEventRequest, state: State) -> Response:
    state.touch_editor(event=body.event)
    log.info(
        "editor_event",
        event=body.event,
        language=body.language,
        session_id=body.session_id,
        user_id=body.user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _desired_state(mode: OrchestratorMode, service: str, managed_names: frozenset[str]) -> str:
    if mode == "maximum":
        return "running"
    if mode == "power_saving" and service in managed_names:
        return "stopped"
    return "managed"
