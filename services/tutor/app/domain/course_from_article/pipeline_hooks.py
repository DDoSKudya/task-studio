from __future__ import annotations

import uuid

import httpx
from app.config import TutorConfig
from app.domain.llm.target import LlmTarget
from studio_contracts.tutor_schemas import TutorSettings


async def _fetch_user_settings(
    client: httpx.AsyncClient,
    config: TutorConfig,
    user_id: uuid.UUID,
) -> TutorSettings:
    from app.domain import course_from_article as pkg

    return await pkg.fetch_user_settings(client, config, user_id)


def _resolve_llm_target(
    config: TutorConfig,
    *,
    provider_url: str | None,
    api_key_encrypted: str | None,
    model: str | None,
) -> LlmTarget | None:
    from app.domain import course_from_article as pkg

    return pkg.resolve_llm_target(
        config,
        provider_url=provider_url,
        api_key_encrypted=api_key_encrypted,
        model=model,
    )


def _is_ollama_target(config: TutorConfig, target: LlmTarget) -> bool:
    from app.domain import course_from_article as pkg

    return bool(pkg.is_ollama_target(config, target))


async def _stage_json(
    client: httpx.AsyncClient,
    target: object,
    *,
    compact: bool,
    stage: str,
    user_message: str,
    max_tokens: int,
) -> dict[str, object]:
    from app.domain import course_from_article as pkg

    payload = await pkg._stage_json(
        client,
        target,
        compact=compact,
        stage=stage,
        user_message=user_message,
        max_tokens=max_tokens,
    )
    return payload
