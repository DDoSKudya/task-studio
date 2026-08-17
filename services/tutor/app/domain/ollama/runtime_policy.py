from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from app.domain.ollama.hardware import (
    HostHardware,
    probe_host_hardware,
    recommend_chat_model,
    recommend_profile,
)

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
        "course": "qwen2.5:3b",
        "polish": "qwen2.5:3b",
        "embed": "nomic-embed-text",
        "max_parallel": 1,
        "num_ctx_compact": 3072,
        "num_ctx_full": 4096,
        "read_timeout": 1200.0,
    },
    "cpu-balanced": {
        "chat": "qwen2.5:3b",
        "course": "qwen2.5:3b",
        "polish": "qwen2.5:3b",
        "embed": "nomic-embed-text",
        "max_parallel": 1,
        "num_ctx_compact": 4096,
        "num_ctx_full": 4096,
        "read_timeout": 900.0,
    },
    "gpu-light": {
        "chat": "qwen2.5:7b",
        "course": "qwen2.5:7b",
        "polish": "qwen2.5:7b",
        "embed": "nomic-embed-text",
        "max_parallel": 1,
        "num_ctx_compact": 4096,
        "num_ctx_full": 8192,
        "read_timeout": 900.0,
    },
    "gpu-balanced": {
        "chat": "qwen2.5:7b",
        "course": "qwen2.5:7b",
        "polish": "qwen2.5:7b",
        "embed": "nomic-embed-text",
        "max_parallel": 1,
        "num_ctx_compact": 4096,
        "num_ctx_full": 8192,
        "read_timeout": 720.0,
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
    hardware: HostHardware | None = None


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


def resolve_profile(
    *,
    accelerator: OllamaAccelerator,
    explicit: str | None,
    hardware: HostHardware | None = None,
) -> OllamaProfile:
    parsed = _parse_profile(explicit or "")
    if parsed is not None:
        return parsed
    hw = hardware or probe_host_hardware()
    if accelerator == "cpu":
        ram = hw.system_ram_gb
        return "cpu-light" if ram is not None and ram <= 8 else "cpu-balanced"
    if accelerator == "gpu" or hw.gpu_available:
        return recommend_profile(
            HostHardware(
                gpu_available=True,
                gpu_vram_gb=hw.gpu_vram_gb,
                system_ram_gb=hw.system_ram_gb,
                source=hw.source,
            )
        )
    return recommend_profile(hw)


def _is_below_course_minimum(model: str) -> bool:
    name = model.casefold()
    return name.endswith(":1.5b") or ":1.5b" in name


def load_ollama_runtime_policy(*, fallback_model: str) -> OllamaRuntimePolicy:
    accelerator = _parse_accelerator(os.getenv("OLLAMA_ACCELERATOR", "auto"))
    hardware = probe_host_hardware()
    profile = resolve_profile(
        accelerator=accelerator,
        explicit=os.getenv("OLLAMA_PROFILE"),
        hardware=hardware,
    )
    defaults = _PROFILE_DEFAULTS[profile]
    routing = os.getenv("OLLAMA_TASK_ROUTING", "true").strip().casefold() not in {
        "0",
        "false",
        "no",
    }
    chat_from_hw = recommend_chat_model(hardware)
    profile_course = str(defaults["course"])

    env_chat = (os.getenv("OLLAMA_MODEL_CHAT") or "").strip()
    env_course = (os.getenv("OLLAMA_MODEL_COURSE") or "").strip()
    env_polish = (os.getenv("OLLAMA_MODEL_POLISH") or "").strip()

    model_course = (
        env_course if env_course and not _is_below_course_minimum(env_course) else profile_course
    )
    model_polish = (
        env_polish if env_polish and not _is_below_course_minimum(env_polish) else model_course
    )
    model_chat = env_chat or chat_from_hw or str(defaults["chat"])

    safe_fallback = fallback_model
    if _is_below_course_minimum(safe_fallback):
        safe_fallback = model_course

    return OllamaRuntimePolicy(
        accelerator=accelerator,
        profile=profile,
        fallback_model=safe_fallback,
        model_chat=model_chat,
        model_course=model_course,
        model_polish=model_polish,
        model_embed=os.getenv("OLLAMA_MODEL_EMBED") or str(defaults["embed"]),
        request_retries=max(0, int(os.getenv("OLLAMA_REQUEST_RETRIES", "3"))),
        max_parallel=max(1, int(os.getenv("OLLAMA_MAX_PARALLEL") or defaults["max_parallel"])),
        num_ctx_compact=int(os.getenv("OLLAMA_NUM_CTX_COMPACT") or defaults["num_ctx_compact"]),
        num_ctx_full=int(os.getenv("OLLAMA_NUM_CTX") or defaults["num_ctx_full"]),
        read_timeout_seconds=float(
            os.getenv("OLLAMA_READ_TIMEOUT_SECONDS") or defaults["read_timeout"]
        ),
        task_routing_enabled=routing,
        hardware=hardware,
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
    normalized = stage.strip().casefold()
    if normalized in {
        "analyze",
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


def profile_default_models(profile: OllamaProfile) -> dict[str, str]:
    defaults = _PROFILE_DEFAULTS[profile]
    return {
        "chat": str(defaults["chat"]),
        "course": str(defaults["course"]),
        "polish": str(defaults["polish"]),
        "embed": str(defaults["embed"]),
    }
