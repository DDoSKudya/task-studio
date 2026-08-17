from __future__ import annotations

import logging
from typing import Any

import httpx
from app.domain.course_from_article.common.runtime.course_context import (
    get_course_profile,
    get_strategy_pack,
)
from app.domain.course_from_article.common.runtime.llm_limits import (
    COURSE_LLM,
    json_stage_continues,
    json_stage_temperature,
    json_stage_top_p,
)
from app.domain.course_from_article.workflow.events.progress_events import (
    _band_progress,
    _sse_event,
    _stage_event,
)
from app.domain.errors import TutorError
from app.domain.llm import LlmTarget, complete_json_raw_until_done, is_ollama_target
from app.domain.llm.transport.request import looks_like_ollama_endpoint
from app.domain.llm.transport.retry import retry_until_mapping
from app.domain.ollama.runtime_policy import num_ctx_for_task
from app.domain.prompt_compose import course_from_article_system_prompt
from fastapi import status

logger = logging.getLogger(__name__)
_STAGE_JSON_RETRIES = COURSE_LLM.stage_retries

__all__ = [
    "_band_progress",
    "_parse_json_object",
    "_sse_event",
    "_stage_event",
    "_stage_json",
]


async def _stage_json(
    client: httpx.AsyncClient,
    target: object,
    *,
    compact: bool,
    stage: str,
    user_message: str,
    max_tokens: int,
) -> dict[str, Any]:
    assert isinstance(target, LlmTarget)
    from app.config import load_config

    config = load_config()
    num_ctx = target.num_ctx
    if num_ctx is None and compact and is_ollama_target(config, target):
        num_ctx = num_ctx_for_task(config.ollama_runtime, compact=True)
    local = looks_like_ollama_endpoint(target)
    system_prompt = course_from_article_system_prompt(
        stage=stage,
        compact=compact,
        course_profile=get_course_profile(),
        local_runtime=local,
        strategy_pack=get_strategy_pack(),
    )
    last_raw = ""

    async def _generate_raw() -> str:
        nonlocal last_raw
        result = await complete_json_raw_until_done(
            client,
            target,
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            max_continues=json_stage_continues(compact=compact),
            temperature=json_stage_temperature(local_runtime=local, compact=compact),
            top_p=json_stage_top_p(local_runtime=local, compact=compact),
            num_ctx=num_ctx,
        )
        last_raw = result.content
        return result.content

    async def _parse_raw(raw: str) -> dict[str, Any] | None:
        parsed = await _parse_stage_payload(
            client,
            target,
            raw=raw,
            stage=stage,
            compact=compact,
            max_tokens=max_tokens,
        )
        if parsed is None:
            logger.warning("course stage %s returned unusable JSON; retrying", stage)
        return parsed

    try:
        return await retry_until_mapping(
            _generate_raw,
            _parse_raw,
            retries=_STAGE_JSON_RETRIES,
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        from app.domain.llm.errors import llm_http_error_message

        if str(exc).casefold() == "expected json object":
            preview = " ".join((last_raw or "").split())
            if len(preview) > 180:
                preview = f"{preview[:180]}…"
            detail = f"course stage {stage} returned invalid JSON"
            if preview:
                detail = f"{detail}: {preview}"
            raise TutorError(status.HTTP_502_BAD_GATEWAY, detail) from exc
        detail = llm_http_error_message(exc)
        message = f"course stage {stage} failed"
        if detail and detail not in {message, "LLM request failed"}:
            message = f"{message}: {detail}"
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            message,
        ) from exc


async def _parse_stage_payload(
    client: httpx.AsyncClient,
    target: object,
    *,
    raw: str,
    stage: str,
    compact: bool,
    max_tokens: int,
) -> dict[str, Any] | None:
    from app.domain.json_util.repair import parse_or_repair_json

    repair_budget = max(max_tokens, 3200)
    return await parse_or_repair_json(
        client,
        target,
        raw=raw,
        hint=(
            f"course_from_article stage={stage}: return one complete JSON object for this "
            "stage only; close all strings and braces"
        ),
        max_tokens=min(repair_budget, 8000),
        num_ctx=target.num_ctx if isinstance(target, LlmTarget) and compact else None,
    )


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    from app.domain.json_util.repair import extract_json_object

    return extract_json_object(raw)
