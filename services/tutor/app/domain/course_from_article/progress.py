from __future__ import annotations

from typing import Any

import httpx
from app.domain.errors import TutorError
from app.domain.llm import complete_json_raw_until_done
from app.domain.ollama.defaults import OLLAMA_NUM_CTX as _OLLAMA_NUM_CTX
from app.domain.prompt_compose import course_from_article_system_prompt
from fastapi import status

from .progress_events import _band_progress, _sse_event, _stage_event

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
    from app.domain.llm import LlmTarget

    assert isinstance(target, LlmTarget)
    system_prompt = course_from_article_system_prompt(stage=stage, compact=compact)
    try:
        result = await complete_json_raw_until_done(
            client,
            target,
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            max_continues=3 if compact else 6,
            temperature=0.2 if compact else 0.15,
            top_p=0.9 if compact else None,
            num_ctx=_OLLAMA_NUM_CTX if compact else None,
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        from app.domain.llm.errors import llm_http_error_message

        detail = llm_http_error_message(exc)
        message = f"course stage {stage} failed"
        if detail and detail not in {message, "LLM request failed"}:
            message = f"{message}: {detail}"
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            message,
        ) from exc

    parsed = await _parse_stage_payload(
        client,
        target,
        raw=result.content,
        stage=stage,
        compact=compact,
        max_tokens=max_tokens,
    )
    if parsed is not None:
        return parsed

    preview = " ".join((result.content or "").split())
    if len(preview) > 180:
        preview = f"{preview[:180]}…"
    detail = f"course stage {stage} returned invalid JSON"
    if preview:
        detail = f"{detail}: {preview}"
    raise TutorError(status.HTTP_502_BAD_GATEWAY, detail)


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
        num_ctx=_OLLAMA_NUM_CTX if compact else None,
    )


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    from app.domain.json_util.repair import extract_json_object

    return extract_json_object(raw)
