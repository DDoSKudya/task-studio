from __future__ import annotations

import httpx
from app.config import TutorConfig
from app.domain.llm.probe_common import (
    model_is_available,
    parse_ollama_model_names,
    probe_external,
    resolve_installed_model,
)
from studio_contracts.tutor_schemas import TutorLlmStatus

__all__ = [
    "model_is_available",
    "probe_external",
    "probe_ollama",
    "resolve_installed_model",
]


async def probe_ollama(client: httpx.AsyncClient, config: TutorConfig) -> TutorLlmStatus:
    if not config.ollama_url:
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail="OLLAMA_URL is not configured",
            default_model=config.ollama_model or None,
        )
    try:
        response = await client.get(f"{config.ollama_url}/api/tags", timeout=8.0)
    except httpx.HTTPError as exc:
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail=f"Ollama unreachable ({exc.__class__.__name__})",
            default_model=config.ollama_model or None,
        )
    if response.status_code >= 400:
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail=f"Ollama responded with HTTP {response.status_code}",
            default_model=config.ollama_model or None,
        )
    try:
        payload = response.json()
    except ValueError:
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail="Ollama returned invalid JSON",
            default_model=config.ollama_model or None,
        )
    models = parse_ollama_model_names(payload)
    default = config.ollama_model or None
    if not models:
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail="Ollama is up, but no models are installed. Pull one (e.g. llama3.2).",
            models=[],
            default_model=default,
        )
    resolved = resolve_installed_model(default, models)
    if default and resolved is None:
        detail = (
            f"Ollama is up, but model {default!r} is not pulled. Available: {', '.join(models[:8])}"
        )
        return TutorLlmStatus(
            ok=False,
            provider="ollama",
            detail=detail,
            models=models,
            default_model=default,
        )
    return TutorLlmStatus(
        ok=True,
        provider="ollama",
        detail=f"Ollama is available ({len(models)} model(s))",
        models=models,
        default_model=resolved or default,
    )
