from __future__ import annotations

from typing import Any

import httpx
from app.domain.json_util.extract import extract_json_object

_REPAIR_SYSTEM = (
    "You repair malformed JSON for Task Studio. "
    "Return ONE JSON object only — no markdown fences, no commentary, no apologies. "
    "Preserve the original intent and keys. Fix syntax only; do not invent new fields."
)

__all__ = [
    "extract_json_object",
    "repair_json_completion",
    "parse_or_repair_json",
]


async def repair_json_completion(
    client: httpx.AsyncClient,
    target: object,
    *,
    broken: str,
    hint: str,
    max_tokens: int = 1200,
    num_ctx: int | None = None,
) -> str:

    from app.domain.llm import LlmTarget, complete_json_chat_completion

    assert isinstance(target, LlmTarget)
    clipped = broken.strip()
    if len(clipped) > 12_000:
        clipped = clipped[:12_000]
    user_message = (
        f"<repair_hint>\n{hint}\n</repair_hint>\n\n"
        f"<broken_output>\n{clipped}\n</broken_output>\n\n"
        "Return the corrected JSON object only."
    )
    return await complete_json_chat_completion(
        client,
        target,
        system_prompt=_REPAIR_SYSTEM,
        user_message=user_message,
        temperature=0.0,
        top_p=0.9 if num_ctx else None,
        max_tokens=max_tokens,
        num_ctx=num_ctx,
    )


async def parse_or_repair_json(
    client: httpx.AsyncClient,
    target: object,
    *,
    raw: str,
    hint: str,
    max_tokens: int = 1200,
    num_ctx: int | None = None,
) -> dict[str, Any] | None:
    parsed = extract_json_object(raw)
    if parsed is not None:
        return parsed
    try:
        repaired = await repair_json_completion(
            client,
            target,
            broken=raw,
            hint=hint,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
        )
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    return extract_json_object(repaired)
