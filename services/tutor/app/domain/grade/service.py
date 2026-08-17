from __future__ import annotations

import uuid
from contextlib import suppress

import httpx
from app.config import TutorConfig
from app.domain.context import fetch_user_settings
from app.domain.errors import TutorError
from app.domain.grade.llm import grade_via_llm
from app.domain.grade.payload import normalize_grade_payload, parse_grade_json
from app.domain.llm import course_provider_url, resolve_llm_target
from studio_contracts.api.tutor_schemas import TutorGradeRequest, TutorGradeResponse, TutorSettings

_normalize_grade_payload = normalize_grade_payload
_parse_grade_json = parse_grade_json


async def grade_submission(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: TutorGradeRequest,
) -> TutorGradeResponse:
    settings = TutorSettings()

    with suppress(TutorError):
        settings = await fetch_user_settings(client, config, user_id)

    target = resolve_llm_target(
        config,
        provider_url=course_provider_url(
            config,
            provider_url=settings.provider_url,
            active_provider=getattr(settings, "active_provider", None),
        ),
        api_key_encrypted=settings.api_key_encrypted,
        model=settings.model,
        task="grade",
    )
    if target is None:
        return TutorGradeResponse(
            passed=False,
            confidence=0.0,
            feedback="LLM grader unavailable",
            usable=False,
        )

    return await grade_via_llm(client, config, target, body)
