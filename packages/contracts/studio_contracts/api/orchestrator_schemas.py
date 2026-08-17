from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OrchestratorMode = Literal["balancing", "maximum", "power_saving"]


class ManagedServiceStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    service: str
    running: bool
    desired: str


class OrchestratorStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    mode: OrchestratorMode
    free_ram_mb: int | None = None
    load_average: float | None = None
    all_users_external_llm: bool | None = None
    grading_cpu_hot: bool = False
    managed_services: list[ManagedServiceStatus] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OrchestratorModeRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    mode: OrchestratorMode


class TutorLlmSummaryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    user_count: int
    local_fallback_users: int
    all_external: bool
