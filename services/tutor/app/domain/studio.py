from __future__ import annotations

import json
import re
import uuid

import httpx
from app.config import TutorConfig
from app.domain.context import fetch_user_settings
from app.domain.errors import TutorError
from app.domain.llm import complete_chat_completion, resolve_llm_target
from app.domain.prompts import load_prompt
from fastapi import status
from studio_contracts.studio_schemas import StudioSuggestRequest, StudioSuggestResponse

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


async def suggest_pack_fragment(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: StudioSuggestRequest,
) -> StudioSuggestResponse:
    user_settings = await fetch_user_settings(client, config, user_id)
    target = resolve_llm_target(
        config,
        provider_url=user_settings.provider_url,
        api_key_encrypted=user_settings.api_key_encrypted,
        model=user_settings.model,
    )
    if target is None:
        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no tutor provider configured")

    try:
        raw = await complete_chat_completion(
            client,
            target,
            system_prompt=load_prompt("pack_studio/pack_studio_generate"),
            user_message=_user_message(body),
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "tutor provider error") from exc

    return StudioSuggestResponse(suggestion=_parse_suggestion(raw))


def _user_message(body: StudioSuggestRequest) -> str:
    parts = [
        f"Context: {body.context}",
        f"Step kind: {body.step_kind}",
        f"Author request: {body.prompt}",
    ]
    if body.manifest_fragment:
        parts.append(f"Current fragment: {json.dumps(body.manifest_fragment, ensure_ascii=False)}")
    return "\n".join(parts)


def _parse_suggestion(raw: str) -> dict[str, object]:
    text = _JSON_FENCE.sub("", raw.strip()).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "tutor returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "tutor suggestion must be a JSON object")
    return parsed
