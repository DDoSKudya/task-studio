from __future__ import annotations

import re
from typing import Literal

from app.domain.llm.probe.probe_parse import model_is_available, resolve_installed_model
from app.domain.ollama.runtime_policy import (
    LlmTaskKind,
    OllamaProfile,
    OllamaRuntimePolicy,
    model_for_task,
    models_to_warm,
    profile_default_models,
)

_COURSE_LADDER: tuple[str, ...] = (
    "qwen2.5:7b",
    "qwen2.5:3b",
)
_CHAT_LADDER: tuple[str, ...] = (
    "qwen2.5:7b",
    "qwen2.5:3b",
    "qwen2.5:1.5b",
)

_PROFILE_CEILING: dict[OllamaProfile, str] = {
    "cpu-light": "qwen2.5:3b",
    "cpu-balanced": "qwen2.5:7b",
    "gpu-light": "qwen2.5:7b",
    "gpu-balanced": "qwen2.5:7b",
}

_COURSE_TASKS = frozenset({"course_outline", "course_topic_bundle", "polish"})


def profile_model_bundle(profile: OllamaProfile) -> dict[str, str]:
    return profile_default_models(profile)


_SIZE_RE = re.compile(r"(?:^|[:\-_/.])(\d+(?:\.\d+)?)b\b", re.IGNORECASE)
_COURSE_MIN_BILLIONS = 3.0
_COURSE_STANDARD_BILLIONS = 7.0

CourseModelTier = Literal["cpu", "standard"]


def course_param_billions(model: str) -> float | None:
    found = [float(match) for match in _SIZE_RE.findall(model.casefold())]
    if not found:
        return None
    return max(found)


def model_is_course_capable(model: str) -> bool:
    size = course_param_billions(model)
    return size is not None and size >= _COURSE_MIN_BILLIONS


def course_model_tier(model: str) -> CourseModelTier | None:

    size = course_param_billions(model)
    if size is None or size < _COURSE_MIN_BILLIONS:
        return None
    return "cpu" if size < _COURSE_STANDARD_BILLIONS else "standard"


def _ladder_for_task(task: LlmTaskKind) -> tuple[str, ...]:
    if task in _COURSE_TASKS:
        return _COURSE_LADDER
    if task == "embeddings":
        return ("nomic-embed-text",)
    return _CHAT_LADDER


def _ceiling_index(profile: OllamaProfile, ladder: tuple[str, ...]) -> int:
    ceiling = _PROFILE_CEILING[profile]
    for index, name in enumerate(ladder):
        if name == ceiling or name.startswith(f"{ceiling}:"):
            return index
    return len(ladder) - 1


def best_installed_on_ladder(
    installed: list[str],
    *,
    ladder: tuple[str, ...],
    ceiling_index: int,
) -> str | None:
    allowed = ladder[: ceiling_index + 1]
    for candidate in allowed:
        resolved = resolve_installed_model(candidate, installed)
        if resolved:
            return resolved
    return None


def resolve_task_model(
    policy: OllamaRuntimePolicy,
    task: LlmTaskKind,
    *,
    installed: list[str] | None = None,
) -> tuple[str | None, bool]:
    wanted = model_for_task(policy, task)
    if installed is None:
        return wanted, False
    if model_is_available(wanted, installed):
        resolved = resolve_installed_model(wanted, installed) or wanted
        if task in _COURSE_TASKS and not model_is_course_capable(resolved):
            return None, True
        return resolved, False
    ladder = _ladder_for_task(task)
    ceiling = _ceiling_index(policy.profile, ladder)
    picked = best_installed_on_ladder(
        installed,
        ladder=ladder,
        ceiling_index=ceiling,
    ) or best_installed_on_ladder(
        installed,
        ladder=ladder,
        ceiling_index=len(ladder) - 1,
    )
    if picked:
        if task in _COURSE_TASKS and not model_is_course_capable(picked):
            return None, True
        return picked, True
    return None, True


def missing_profile_models(
    policy: OllamaRuntimePolicy,
    installed: list[str],
) -> list[str]:
    return [name for name in models_to_warm(policy) if not model_is_available(name, installed)]
