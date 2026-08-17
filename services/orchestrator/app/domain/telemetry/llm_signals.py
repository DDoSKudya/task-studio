from __future__ import annotations

from app.config import OrchestratorSettings
from studio_contracts.api.orchestrator_schemas import TutorLlmSummaryResponse


def ollama_stop_reason(*, low_ram: bool, grading_cpu_hot: bool) -> str:
    if low_ram:
        return "low_ram"
    if grading_cpu_hot:
        return "grading_cpu_hot"
    return "all_users_external_llm"


def all_users_external(
    settings: OrchestratorSettings,
    summary: TutorLlmSummaryResponse | None,
) -> bool:
    if settings.tutor_default_provider_url:
        return True
    if summary is None:
        return False
    if summary.user_count == 0:
        return True
    return summary.all_external
