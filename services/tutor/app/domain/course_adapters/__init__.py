from __future__ import annotations

from .evaluate import (
    CourseDraft,
    EvalReport,
    adapter_beats_compiler,
    compiler_baseline,
    evaluate_corpus,
    report_from_dict,
)
from .export import TrainJob, export_gguf_to_ollama, prepare_train_job
from .gold import GoldPair, GoldStore, assert_gold_ready, harvest_from_build
from .registry import AdapterRegistry, load_registry
from .roles import ADAPTER_ROLES, AdapterRefused, AdapterRole, ollama_model_for_role
from .runtime import apply_role_adapter, load_runtime_registry
from .ship import ship_adapter

__all__ = [
    "ADAPTER_ROLES",
    "AdapterRefused",
    "AdapterRegistry",
    "AdapterRole",
    "CourseDraft",
    "EvalReport",
    "GoldPair",
    "GoldStore",
    "TrainJob",
    "adapter_beats_compiler",
    "apply_role_adapter",
    "assert_gold_ready",
    "compiler_baseline",
    "evaluate_corpus",
    "export_gguf_to_ollama",
    "harvest_from_build",
    "load_registry",
    "load_runtime_registry",
    "ollama_model_for_role",
    "prepare_train_job",
    "report_from_dict",
    "ship_adapter",
]
