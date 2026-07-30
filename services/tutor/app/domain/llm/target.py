from __future__ import annotations

import base64
from dataclasses import dataclass

from app.config import TutorConfig
from studio_common.crypto import decrypt_bytes


@dataclass(frozen=True, slots=True)
class LlmTarget:
    base_url: str
    api_key: str | None
    model: str


def resolve_llm_target(
    config: TutorConfig,
    *,
    provider_url: str | None,
    api_key_encrypted: str | None,
    model: str | None,
) -> LlmTarget | None:
    resolved_model = model or config.ollama_model
    api_key = decrypt_tutor_api_key(config.secrets_master_key, api_key_encrypted)

    if provider_url:
        return LlmTarget(provider_url.rstrip("/"), api_key, resolved_model)
    if config.default_provider_url:
        return LlmTarget(config.default_provider_url, api_key, resolved_model)
    if config.ollama_url:
        return LlmTarget(f"{config.ollama_url}/v1", None, resolved_model)
    return None


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
