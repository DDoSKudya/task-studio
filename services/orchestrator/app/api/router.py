from __future__ import annotations

import structlog
from fastapi import APIRouter, status
from starlette.responses import Response
from studio_contracts.orchestrator_schemas import (
    ManagedServiceStatus,
    OrchestratorMode,
    OrchestratorModeRequest,
    OrchestratorStatusResponse,
)

from app.api.router_deps import (
    EditorEventRequest,
    ManagedNames,
    State,
    SystemAuth,
    desired_state,
)

router = APIRouter(prefix="/internal/v1/orchestrator", tags=["orchestrator"])
log = structlog.get_logger("orchestrator")


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
            desired=desired_state(state.mode, service, managed_names),
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
