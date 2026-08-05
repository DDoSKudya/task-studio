from __future__ import annotations

import uuid

import httpx
from app.config import TutorConfig
from app.domain.course.cache import step_page_text
from app.domain.errors import TutorError
from app.domain.fallback_hints.service import hints_for_kind
from app.domain.llm import resolve_llm_target
from fastapi import status
from redis.asyncio import Redis
from studio_contracts.tutor_schemas import TutorHintResponse

from .hints_llm import generate_contextual_hints
from .view import _load_tutor_view

_generate_contextual_hints = generate_contextual_hints


async def build_hints(
    client: httpx.AsyncClient,
    redis: Redis,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    step_id: str,
) -> TutorHintResponse:
    view = await _load_tutor_view(
        client,
        redis,
        config,
        user_id=user_id,
        session_id=session_id,
    )
    if view.step.step_id != step_id:
        raise TutorError(status.HTTP_404_NOT_FOUND, "step not found")

    page = step_page_text(view.step)
    if view.step.kind == "video" and not page:
        return TutorHintResponse(
            hints=[
                "This step is video-only. Without a transcript, content hints are unavailable.",
                "Rewatch the key moments and jot down the main idea in a short note.",
            ],
            source="fallback",
        )

    target = resolve_llm_target(
        config,
        provider_url=view.user_settings.provider_url,
        api_key_encrypted=view.user_settings.api_key_encrypted,
        model=view.user_settings.model,
        task="hints",
    )
    if target is not None:
        try:
            generated = await generate_contextual_hints(
                client,
                target,
                config=config,
                view=view,
                page=page,
            )
            if generated:
                return TutorHintResponse(hints=generated, source="llm")
        except (httpx.HTTPError, ValueError, TypeError):
            pass

    return TutorHintResponse(hints=hints_for_kind(view.step.kind), source="fallback")
