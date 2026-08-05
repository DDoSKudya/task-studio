from __future__ import annotations

import base64
from dataclasses import dataclass, replace

from app.config import TutorConfig
from app.domain.ollama.runtime_policy import LlmTaskKind, model_for_task, num_ctx_for_task
from studio_common.crypto import decrypt_bytes


@dataclass(frozen=True, slots=True)
class LlmTarget:
    base_url: str
    api_key: str | None
    model: str
    read_timeout_seconds: float | None = None
    request_retries: int | None = None
    num_ctx: int | None = None


def resolve_llm_target(
    config: TutorConfig,
    *,
    provider_url: str | None,
    api_key_encrypted: str | None,
    model: str | None,
    task: LlmTaskKind = "default",
) -> LlmTarget | None:
    """Собрать цель LLM с учётом контура (`task`: chat / grade / course / …)."""
    api_key = decrypt_tutor_api_key(config.secrets_master_key, api_key_encrypted)
    policy = config.ollama_runtime
    ollama_model = model or model_for_task(policy, task) or config.ollama_model
    runtime_kwargs = {
        "read_timeout_seconds": policy.read_timeout_seconds,
        "request_retries": policy.request_retries,
        "num_ctx": num_ctx_for_task(policy, task=task),
    }

    if provider_url:
        # Внешний провайдер: модель из настроек; task влияет только на Ollama-lane.
        return LlmTarget(provider_url.rstrip("/"), api_key, model or config.ollama_model)
    if config.default_provider_url:
        return LlmTarget(
            config.default_provider_url,
            api_key,
            model or config.ollama_model,
        )
    if config.ollama_url:
        return LlmTarget(
            f"{config.ollama_url}/v1",
            None,
            ollama_model,
            **runtime_kwargs,
        )
    return None


def with_task(target: LlmTarget, config: TutorConfig, task: LlmTaskKind) -> LlmTarget:
    if not is_ollama_target(config, target):
        return target
    policy = config.ollama_runtime
    return replace(
        target,
        model=model_for_task(policy, task),
        num_ctx=num_ctx_for_task(policy, task=task),
        read_timeout_seconds=policy.read_timeout_seconds,
        request_retries=policy.request_retries,
    )


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
