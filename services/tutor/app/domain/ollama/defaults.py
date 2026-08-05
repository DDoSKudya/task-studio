from __future__ import annotations

from app.config import TutorConfig
from app.domain.ollama.runtime_policy import (
    LlmTaskKind,
    OllamaRuntimePolicy,
    load_ollama_runtime_policy,
    model_for_task,
    models_to_warm,
    num_ctx_for_task,
    stage_task_kind,
)

OLLAMA_NUM_CTX = 4096


def num_ctx_for_compact(config: TutorConfig, *, compact: bool) -> int:
    return num_ctx_for_task(config.ollama_runtime, compact=compact)


__all__ = [
    "LlmTaskKind",
    "OLLAMA_NUM_CTX",
    "OllamaRuntimePolicy",
    "load_ollama_runtime_policy",
    "model_for_task",
    "models_to_warm",
    "num_ctx_for_compact",
    "num_ctx_for_task",
    "stage_task_kind",
]
