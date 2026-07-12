from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from studio_contracts.orchestrator_schemas import OrchestratorMode


@dataclass
class ControllerState:
    mode: OrchestratorMode
    editor_open: bool = False
    editor_last_activity: datetime | None = None
    ollama_last_started: datetime | None = None
    warnings: list[str] = field(default_factory=list)
    free_ram_mb: int | None = None
    load_average: float | None = None
    all_users_external_llm: bool | None = None
    grading_cpu_hot: bool = False
    managed_running: dict[str, bool] = field(default_factory=dict)

    def touch_editor(self, *, event: Literal["open", "close"]) -> None:
        now = datetime.now(UTC)
        if event == "open":
            self.editor_open = True
            self.editor_last_activity = now
            return
        self.editor_open = False
        self.editor_last_activity = now

    def minutes_since(self, moment: datetime | None) -> float | None:
        if moment is None:
            return None
        return (datetime.now(UTC) - moment).total_seconds() / 60
