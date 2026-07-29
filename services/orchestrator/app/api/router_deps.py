from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from studio_contracts.orchestrator_schemas import OrchestratorMode

from app.config import OrchestratorSettings
from app.domain.state import ControllerState


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


def desired_state(mode: OrchestratorMode, service: str, managed_names: frozenset[str]) -> str:
    if mode == "maximum":
        return "running"
    if mode == "power_saving" and service in managed_names:
        return "stopped"
    return "managed"
