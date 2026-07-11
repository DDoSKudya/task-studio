from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
from app.config import TutorConfig
from app.domain.context import fetch_session, fetch_step, fetch_user_settings
from app.domain.errors import TutorError
from app.domain.hints import hints_for_kind
from app.domain.llm import LlmTarget, resolve_llm_target, stream_chat_completion
from app.domain.prompts import system_prompt_for_phase
from app.domain.rate_limit import check_rate_limits
from fastapi import status
from redis.asyncio import Redis
from studio_contracts.session_schemas import SessionState, StepContent
from studio_contracts.tutor_schemas import (
    TutorHintResponse,
    TutorSettings,
    tutor_allowed,
)


@dataclass(frozen=True, slots=True)
class TutorView:
    session: SessionState
    step: StepContent
    user_settings: TutorSettings


@dataclass(frozen=True, slots=True)
class ChatContext:
    target: LlmTarget
    system_prompt: str


async def build_hints(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    step_id: str,
) -> TutorHintResponse:
    view = await _load_tutor_view(client, config, user_id=user_id, session_id=session_id)
    if view.step.step_id != step_id:
        raise TutorError(status.HTTP_404_NOT_FOUND, "step not found")
    return TutorHintResponse(hints=hints_for_kind(view.step.kind), source="fallback")


async def prepare_chat(
    client: httpx.AsyncClient,
    redis: Redis,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ChatContext:
    view = await _load_tutor_view(client, config, user_id=user_id, session_id=session_id)
    await check_rate_limits(
        redis,
        user_id=str(user_id),
        per_minute_limit=config.rate_limit_per_minute,
        daily_limit=view.user_settings.daily_limit,
    )

    target = resolve_llm_target(
        config,
        provider_url=view.user_settings.provider_url,
        api_key_encrypted=view.user_settings.api_key_encrypted,
        model=view.user_settings.model,
    )
    if target is None:
        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no tutor provider configured")

    system_prompt = system_prompt_for_phase(
        view.session.current_phase,
        step_kind=view.step.kind,
        step_title=view.step.title,
    )
    return ChatContext(target=target, system_prompt=system_prompt)


async def stream_chat(
    client: httpx.AsyncClient,
    context: ChatContext,
    *,
    message: str,
) -> AsyncIterator[bytes]:
    try:
        async for token in stream_chat_completion(
            client,
            context.target,
            system_prompt=context.system_prompt,
            user_message=message,
        ):
            yield _sse_event({"type": "token", "content": token})
        yield _sse_event({"type": "done"})
    except httpx.HTTPError:
        yield _sse_event(
            {
                "type": "error",
                "content": "Tutor is temporarily unavailable. Try static hints.",
            }
        )
        yield _sse_event({"type": "done"})


async def _load_tutor_view(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> TutorView:
    session, user_settings, step = await asyncio.gather(
        fetch_session(client, config, user_id=user_id, session_id=session_id),
        fetch_user_settings(client, config, user_id),
        fetch_step(client, config, user_id=user_id, session_id=session_id),
    )
    _ensure_tutor_allowed(session, user_settings)
    return TutorView(session=session, step=step, user_settings=user_settings)


def _ensure_tutor_allowed(session: SessionState, user_settings: TutorSettings) -> None:
    if not tutor_allowed(
        session.current_phase,
        pack_tutor_enabled=session.policies.tutor_enabled,
        user_enabled=user_settings.enabled,
    ):
        raise TutorError(status.HTTP_403_FORBIDDEN, "tutor disabled")


def _sse_event(payload: dict[str, object]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()
