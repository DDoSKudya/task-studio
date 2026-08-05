from __future__ import annotations

import uuid

import httpx
from app.config import TutorConfig
from app.domain.course.cache import format_course_outline, format_step_context
from app.domain.errors import TutorError
from app.domain.llm import is_ollama_target, resolve_llm_target
from app.domain.prompt_compose import context_budget, step_looks_like_sql, system_prompt_for_phase
from app.domain.rate_limit import check_rate_limits
from fastapi import status
from redis.asyncio import Redis

from .models import ChatContext
from .view import _load_tutor_view


async def prepare_chat(
    client: httpx.AsyncClient,
    redis: Redis,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    skip_rate_limit: bool = False,
) -> ChatContext:
    view = await _load_tutor_view(
        client,
        redis,
        config,
        user_id=user_id,
        session_id=session_id,
    )
    if not skip_rate_limit:
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
        task="chat",
    )
    if target is None:
        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no tutor provider configured")

    compact = is_ollama_target(config, target)
    budget = context_budget(compact=compact)
    sql_aware = step_looks_like_sql(view.step)
    system_prompt = "\n\n".join(
        part
        for part in (
            system_prompt_for_phase(
                view.session.current_phase,
                step_kind=view.step.kind,
                step_title=view.step.title,
                compact=compact,
                sql_aware=sql_aware,
            ),
            format_course_outline(view.digest, max_steps=budget.outline_steps),
            format_step_context(
                view.digest,
                view.step,
                page_limit=budget.page_chars,
                starter_limit=budget.starter_chars,
            ),
        )
        if part
    )
    return ChatContext(
        target=target,
        system_prompt=system_prompt,
        conversation_id=str(session_id),
        compact=compact,
    )
