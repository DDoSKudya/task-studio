from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

OllamaAccelerator = Literal["auto", "gpu", "cpu"]
OllamaProfile = Literal["cpu-light", "cpu-balanced", "gpu-light", "gpu-balanced"]
LlmTaskKind = Literal[
    "chat",
    "hints",
    "grade",
    "course_outline",
    "course_topic_bundle",
    "polish",
    "embeddings",
    "default",
]

_PROFILE_DEFAULTS: dict[OllamaProfile, dict[str, str | int | float]] = {
    "cpu-light": {
        "chat": "qwen2.5:1.5b",
        "course": "qwen2.5:1.5b",
        "polish": "qwen2.5:1.5b",
        "embed": "nomic-embed-text",
        "max_parallel": 1,
        # Course prompts need room for syllabus + excerpt; 2k starves quality.
        "num_ctx_compact": 3072,
        "num_ctx_full": 3072,
        "read_timeout": 900.0,
    },
    "cpu-balanced": {
        "chat": "qwen2.5:3b",
        "course": "qwen2.5:3b",
        "polish": "qwen2.5:3b",
        "embed": "nomic-embed-text",
        "max_parallel": 1,
        "num_ctx_compact": 4096,
        "num_ctx_full": 4096,
        "read_timeout": 720.0,
    },
    "gpu-light": {
        "chat": "qwen2.5:3b",
        "course": "qwen2.5:3b",
        "polish": "qwen2.5:3b",
        "embed": "nomic-embed-text",
        "max_parallel": 2,
        "num_ctx_compact": 4096,
        "num_ctx_full": 4096,
        "read_timeout": 660.0,
    },
    "gpu-balanced": {
        "chat": "qwen2.5:7b",
        "course": "qwen2.5:7b",
        "polish": "qwen2.5:7b",
        "embed": "nomic-embed-text",
        "max_parallel": 2,
        "num_ctx_compact": 4096,
        "num_ctx_full": 8192,
        "read_timeout": 600.0,
    },
}

_TASK_TO_MODEL_KEY: dict[LlmTaskKind, str] = {
    "chat": "chat",
    "hints": "chat",
    "grade": "chat",
    "course_outline": "course",
    "course_topic_bundle": "course",
    "polish": "polish",
    "embeddings": "embed",
    "default": "chat",
}

# Короткие JSON/подсказки — compact ctx; курс и чат — full.
_COMPACT_TASKS: frozenset[LlmTaskKind] = frozenset({"grade", "hints", "polish", "embeddings"})


@dataclass(frozen=True, slots=True)
class OllamaRuntimePolicy:
    accelerator: OllamaAccelerator
    profile: OllamaProfile
    fallback_model: str
    model_chat: str
    model_course: str
    model_polish: str
    model_embed: str
    request_retries: int
    max_parallel: int
    num_ctx_compact: int
    num_ctx_full: int
    read_timeout_seconds: float
    task_routing_enabled: bool


def _parse_accelerator(raw: str) -> OllamaAccelerator:
    value = raw.strip().casefold()
    if value in {"auto", "gpu", "cpu"}:
        return value  # type: ignore[return-value]
    return "auto"


def _parse_profile(raw: str) -> OllamaProfile | None:
    value = raw.strip().casefold()
    if value in {"cpu-light", "cpu-balanced", "gpu-light", "gpu-balanced"}:
        return value  # type: ignore[return-value]
    return None


def _env_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _detect_system_ram_gb() -> float | None:
    env_value = _env_float("OLLAMA_SYSTEM_RAM_GB")
    if env_value is not None and env_value > 0:
        return env_value
    page_size = getattr(os, "sysconf", None)
    if page_size is None:
        return None
    try:
        bytes_total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None
    if bytes_total <= 0:
        return None
    return bytes_total / (1024**3)


def _gpu_available(accelerator: OllamaAccelerator) -> bool:
    if accelerator == "gpu":
        return True
    if accelerator == "cpu":
        return False
    gpu_hint = os.getenv("OLLAMA_GPU_AVAILABLE", "").strip().casefold()
    return gpu_hint in {"1", "true", "yes"}


def resolve_profile(*, accelerator: OllamaAccelerator, explicit: str | None) -> OllamaProfile:
    parsed = _parse_profile(explicit or "")
    if parsed is not None:
        return parsed
    if _gpu_available(accelerator):
        gpu_vram_gb = _env_float("OLLAMA_GPU_VRAM_GB")
        if gpu_vram_gb is not None and gpu_vram_gb < 10:
            return "gpu-light"
        return "gpu-balanced"
    ram_gb = _detect_system_ram_gb()
    if ram_gb is not None and ram_gb <= 8:
        return "cpu-light"
    return "cpu-balanced"


def load_ollama_runtime_policy(*, fallback_model: str) -> OllamaRuntimePolicy:
    accelerator = _parse_accelerator(os.getenv("OLLAMA_ACCELERATOR", "auto"))
    profile = resolve_profile(
        accelerator=accelerator,
        explicit=os.getenv("OLLAMA_PROFILE"),
    )
    defaults = _PROFILE_DEFAULTS[profile]
    routing = os.getenv("OLLAMA_TASK_ROUTING", "true").strip().casefold() not in {
        "0",
        "false",
        "no",
    }
    return OllamaRuntimePolicy(
        accelerator=accelerator,
        profile=profile,
        fallback_model=fallback_model,
        model_chat=os.getenv("OLLAMA_MODEL_CHAT") or str(defaults["chat"]),
        model_course=os.getenv("OLLAMA_MODEL_COURSE") or str(defaults["course"]),
        model_polish=os.getenv("OLLAMA_MODEL_POLISH") or str(defaults["polish"]),
        model_embed=os.getenv("OLLAMA_MODEL_EMBED") or str(defaults["embed"]),
        request_retries=max(0, int(os.getenv("OLLAMA_REQUEST_RETRIES", "3"))),
        max_parallel=max(1, int(os.getenv("OLLAMA_MAX_PARALLEL") or defaults["max_parallel"])),
        num_ctx_compact=int(os.getenv("OLLAMA_NUM_CTX_COMPACT") or defaults["num_ctx_compact"]),
        num_ctx_full=int(os.getenv("OLLAMA_NUM_CTX") or defaults["num_ctx_full"]),
        read_timeout_seconds=float(
            os.getenv("OLLAMA_READ_TIMEOUT_SECONDS") or defaults["read_timeout"]
        ),
        task_routing_enabled=routing,
    )


def model_for_task(policy: OllamaRuntimePolicy, task: LlmTaskKind) -> str:
    if not policy.task_routing_enabled:
        return policy.fallback_model
    key = _TASK_TO_MODEL_KEY.get(task, "chat")
    mapping = {
        "chat": policy.model_chat,
        "course": policy.model_course,
        "polish": policy.model_polish,
        "embed": policy.model_embed,
    }
    return mapping.get(key, policy.fallback_model)


def num_ctx_for_task(
    policy: OllamaRuntimePolicy,
    *,
    compact: bool | None = None,
    task: LlmTaskKind | None = None,
) -> int:
    use_compact = compact
    if use_compact is None:
        use_compact = task in _COMPACT_TASKS if task is not None else False
    return policy.num_ctx_compact if use_compact else policy.num_ctx_full


def stage_task_kind(stage: str) -> LlmTaskKind:
    # Одна course-модель на весь build — смена весов на CPU стоит минут.
    normalized = stage.strip().casefold()
    if normalized in {
        "analyze",
        "consistency",
        "theory",
        "quizzes",
        "code",
        "tasks",
        "topic_bundle",
        "polish",
    }:
        return "course_topic_bundle"
    return "default"


def models_to_warm(policy: OllamaRuntimePolicy) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in (
        policy.fallback_model,
        policy.model_chat,
        policy.model_course,
        policy.model_polish,
        policy.model_embed,
    ):
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered
