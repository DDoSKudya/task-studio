from __future__ import annotations

import uuid

import httpx
from app.config import TutorConfig
from app.domain.chat.session.models import ChatContext
from app.domain.chat.session.rate_limit import check_rate_limits
from app.domain.chat.session.view import load_tutor_view
from app.domain.course.cache import format_course_outline, format_step_context
from app.domain.errors import TutorError
from app.domain.llm import course_provider_url, is_ollama_target, resolve_llm_target
from app.domain.prompt_compose import context_budget, step_looks_like_sql, system_prompt_for_phase
from fastapi import status
from redis.asyncio import Redis


async def prepare_chat(
    client: httpx.AsyncClient,
    redis: Redis,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    skip_rate_limit: bool = False,
) -> ChatContext:
    view = await load_tutor_view(
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

    installed: list[str] | None = None
    provider_url = course_provider_url(
        config,
        provider_url=view.user_settings.provider_url,
        active_provider=getattr(view.user_settings, "active_provider", None),
    )
    if config.ollama_url and not provider_url:
        try:
            from app.domain.ollama.ensure_models import list_ollama_models

            installed = await list_ollama_models(client, ollama_url=config.ollama_url)
        except httpx.HTTPError:
            installed = None

    target = resolve_llm_target(
        config,
        provider_url=provider_url,
        api_key_encrypted=view.user_settings.api_key_encrypted,
        model=view.user_settings.model,
        task="chat",
        installed_models=installed,
    )
    if target is None:
        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no tutor provider configured")

    compact = is_ollama_target(config, target)
    if compact:
        from app.domain.course_adapters.runtime import apply_role_adapter

        target = apply_role_adapter(target, "tutor-chat", installed=installed)
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
