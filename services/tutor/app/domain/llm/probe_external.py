from __future__ import annotations

import httpx
from app.domain.llm.probe_parse import parse_openai_model_ids
from studio_contracts.tutor_schemas import TutorLlmStatus


async def probe_external(
    client: httpx.AsyncClient,
    *,
    provider_url: str,
    api_key: str | None,
    model: str | None,
) -> TutorLlmStatus:
    base = provider_url.rstrip("/")
    if not base:
        return TutorLlmStatus(
            ok=False,
            provider="external",
            detail="Provider URL is required",
            default_model=model,
        )
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = await client.get(f"{base}/models", headers=headers, timeout=12.0)
    except httpx.HTTPError as exc:
        return TutorLlmStatus(
            ok=False,
            provider="external",
            detail=f"Endpoint unreachable ({exc.__class__.__name__})",
            default_model=model,
        )
    if response.status_code >= 400:
        return TutorLlmStatus(
            ok=False,
            provider="external",
            detail=f"Endpoint responded with HTTP {response.status_code}",
            default_model=model,
        )
    try:
        payload = response.json()
    except ValueError:
        payload = None
    models = parse_openai_model_ids(payload)
    return TutorLlmStatus(
        ok=True,
        provider="external",
        detail="Endpoint is available",
        models=models[:200],
        default_model=model,
    )
