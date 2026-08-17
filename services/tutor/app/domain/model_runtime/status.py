from __future__ import annotations

from typing import Literal

import httpx
from app.config import TutorConfig
from app.domain.llm.probe.probe_common import (
    model_is_available,
    probe_external,
    resolve_installed_model,
)
from app.domain.ollama.ensure_models import ensure_profile_models
from app.domain.ollama.model_select import resolve_task_model
from app.domain.ollama.runtime_policy import OllamaRuntimePolicy, model_for_task, models_to_warm
from studio_contracts.api.tutor_schemas import TutorLlmStatus

__all__ = [
    "model_is_available",
    "probe_external",
    "probe_ollama",
    "resolve_installed_model",
]

CoursePipeline = Literal["compact", "full"]


def _managed_status(
    *,
    ok: bool,
    detail: str,
    policy: OllamaRuntimePolicy,
    pipeline: CoursePipeline,
    installed: list[str],
    missing: list[str],
    default_model: str | None,
    course_model: str,
    chat_model: str,
) -> TutorLlmStatus:
    return TutorLlmStatus(
        ok=ok,
        provider="ollama",
        detail=detail,
        models=installed,
        default_model=default_model,
        ollama_profile=policy.profile,
        recommended_models=missing,
        course_pipeline=pipeline,
        active_course_model=course_model,
        active_chat_model=chat_model,
        model_managed=True,
    )


async def probe_ollama(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    ensure: bool = False,
) -> TutorLlmStatus:
    if not config.ollama_url:
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail="OLLAMA_URL is not configured",
            default_model=config.ollama_model or None,
        )
    policy = config.ollama_runtime
    pipeline: CoursePipeline = "full"
    try:
        installed, missing, pulled = await ensure_profile_models(
            client,
            ollama_url=config.ollama_url,
            policy=policy,
            pull=ensure,
        )
    except httpx.HTTPError as exc:
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail=f"Ollama unreachable ({exc.__class__.__name__})",
            default_model=config.ollama_model or None,
            ollama_profile=policy.profile,
            course_pipeline=pipeline,
        )

    wanted_course = model_for_task(policy, "course_topic_bundle")
    wanted_chat = model_for_task(policy, "chat")
    course_model, course_fallback = resolve_task_model(
        policy, "course_topic_bundle", installed=installed
    )
    chat_model, chat_fallback = resolve_task_model(policy, "chat", installed=installed)

    if not installed or course_model is None:
        detail = (
            "Ollama is up, but no course-capable model is installed "
            f"(minimum qwen2.5:3b). Pull {wanted_course}."
        )
        if installed:
            detail = (
                f"Ollama has {len(installed)} model(s), but none are course-capable "
                f"(minimum qwen2.5:3b). Pull {wanted_course} or qwen2.5:7b."
            )
        return _managed_status(
            ok=False,
            detail=detail,
            policy=policy,
            pipeline=pipeline,
            installed=installed,
            missing=missing or models_to_warm(policy),
            default_model=wanted_course,
            course_model="",
            chat_model="",
        )

    notes: list[str] = []
    if pulled:
        notes.append(f"pulled: {', '.join(pulled[:4])}")
    if missing:
        notes.append(f"still missing: {', '.join(missing[:4])}")
    if course_fallback:
        notes.append(f"course using fallback {course_model!r} (wanted {wanted_course!r})")
    if chat_fallback and chat_model:
        notes.append(f"chat using fallback {chat_model!r} (wanted {wanted_chat!r})")
    notes.append(f"course pipeline={pipeline}")
    detail = f"Ollama is available ({len(installed)} model(s)). {'; '.join(notes)}"

    return _managed_status(
        ok=True,
        detail=detail,
        policy=policy,
        pipeline=pipeline,
        installed=installed,
        missing=missing,
        default_model=course_model,
        course_model=course_model or "",
        chat_model=chat_model or "",
    )
