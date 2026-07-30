from __future__ import annotations

from app.api.deps import ClientDep, ConfigDep, UserId
from app.domain.context import fetch_user_settings
from app.domain.llm import decrypt_tutor_api_key
from app.domain.status import probe_external, probe_ollama
from fastapi import APIRouter
from studio_contracts.tutor_schemas import TutorLlmStatus, TutorLlmTestRequest

router = APIRouter()


@router.get("/llm-status", response_model=TutorLlmStatus)
async def llm_status(
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> TutorLlmStatus:
    _ = user_id
    return await probe_ollama(client, config)


@router.post("/llm-test", response_model=TutorLlmStatus)
async def llm_test(
    body: TutorLlmTestRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> TutorLlmStatus:
    if body.provider == "external":
        provider_url = (body.provider_url or "").strip()
        api_key = (body.api_key or "").strip() or None
        if not api_key:
            user_settings = await fetch_user_settings(client, config, user_id)
            cleaned = provider_url.casefold()
            mode = "cursor" if "cursor-proxy" in cleaned else "external" if cleaned else None
            encrypted: str | None = None
            if mode:
                profile = user_settings.provider_profiles.get(mode)
                if profile and profile.api_key_encrypted:
                    encrypted = profile.api_key_encrypted
            if not encrypted:
                encrypted = user_settings.api_key_encrypted
            api_key = decrypt_tutor_api_key(config.secrets_master_key, encrypted)
        return await probe_external(
            client,
            provider_url=provider_url,
            api_key=api_key,
            model=(body.model or "").strip() or None,
        )
    return await probe_ollama(client, config)
