from __future__ import annotations

import base64
from dataclasses import dataclass, replace

from app.config import TutorConfig
from app.domain.ollama.runtime_policy import LlmTaskKind, num_ctx_for_task
from studio_common.security.crypto import decrypt_bytes


@dataclass(frozen=True, slots=True)
class LlmTarget:
    base_url: str
    api_key: str | None
    model: str
    read_timeout_seconds: float | None = None
    request_retries: int | None = None
    num_ctx: int | None = None
    installed_models: tuple[str, ...] | None = None


def resolve_llm_target(
    config: TutorConfig,
    *,
    provider_url: str | None,
    api_key_encrypted: str | None,
    model: str | None,
    task: LlmTaskKind = "default",
    installed_models: list[str] | None = None,
) -> LlmTarget | None:
    api_key = decrypt_tutor_api_key(config.secrets_master_key, api_key_encrypted)
    policy = config.ollama_runtime
    runtime_kwargs = {
        "read_timeout_seconds": policy.read_timeout_seconds,
        "request_retries": policy.request_retries,
        "num_ctx": num_ctx_for_task(policy, task=task),
    }

    if provider_url:
        cursor = "cursor-proxy" in provider_url.casefold()
        chosen = (model or "").strip() or ("auto" if cursor else config.ollama_model)
        return LlmTarget(
            provider_url.rstrip("/"),
            api_key,
            chosen,
            read_timeout_seconds=900.0 if cursor else None,
        )
    if config.default_provider_url:
        return LlmTarget(
            config.default_provider_url,
            api_key,
            model or config.ollama_model,
        )
    if config.ollama_url:
        from app.domain.ollama.model_select import resolve_task_model

        ollama_model, _ = resolve_task_model(policy, task, installed=installed_models)
        if not ollama_model:
            return None
        return LlmTarget(
            f"{config.ollama_url}/v1",
            None,
            ollama_model,
            **runtime_kwargs,
            installed_models=(tuple(installed_models) if installed_models is not None else None),
        )
    return None


def with_task(
    target: LlmTarget,
    config: TutorConfig,
    task: LlmTaskKind,
    *,
    installed_models: list[str] | None = None,
) -> LlmTarget:
    if not is_ollama_target(config, target):
        return target
    from app.domain.ollama.model_select import resolve_task_model

    policy = config.ollama_runtime
    model, _ = resolve_task_model(policy, task, installed=installed_models)
    if not model:
        return target
    return replace(
        target,
        model=model,
        num_ctx=num_ctx_for_task(policy, task=task),
        read_timeout_seconds=policy.read_timeout_seconds,
        request_retries=policy.request_retries,
        installed_models=(
            tuple(installed_models) if installed_models is not None else target.installed_models
        ),
    )


def course_provider_url(
    config: TutorConfig,
    *,
    provider_url: str | None,
    active_provider: str | None = None,
) -> str | None:

    provider_name = active_provider.strip() if isinstance(active_provider, str) else ""
    if provider_name.casefold() == "ollama":
        return None
    raw = provider_url.strip() if isinstance(provider_url, str) else ""
    if not raw:
        return None
    folded = raw.casefold()
    if "127.0.0.1" in folded or "localhost" in folded or "[::1]" in folded:
        return None
    if is_ollama_target(config, LlmTarget(raw.rstrip("/"), None, "x")):
        return None
    return raw


def is_ollama_target(config: TutorConfig, target: LlmTarget) -> bool:
    if not config.ollama_url:
        return False
    base = target.base_url.rstrip("/")
    ollama = config.ollama_url.rstrip("/")
    return base in {ollama, f"{ollama}/v1"}


def is_cursor_target(target: LlmTarget) -> bool:
    return "cursor-proxy" in target.base_url.casefold()


def decrypt_tutor_api_key(master_key: str | None, encrypted_b64: str | None) -> str | None:
    if not encrypted_b64 or not master_key:
        return None
    try:
        payload = base64.b64decode(encrypted_b64)
        return decrypt_bytes(payload, key_b64=master_key).decode("utf-8")
    except ValueError:
        return None
