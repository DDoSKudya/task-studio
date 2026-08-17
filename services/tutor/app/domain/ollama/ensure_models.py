from __future__ import annotations

import httpx
from app.domain.llm.probe.probe_parse import model_is_available, parse_ollama_model_names
from app.domain.ollama.runtime_policy import OllamaRuntimePolicy, models_to_warm


async def list_ollama_models(client: httpx.AsyncClient, *, ollama_url: str) -> list[str]:
    response = await client.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=8.0)
    response.raise_for_status()
    return parse_ollama_model_names(response.json())


async def pull_ollama_model(
    client: httpx.AsyncClient,
    *,
    ollama_url: str,
    model: str,
    timeout_seconds: float = 1800.0,
) -> None:
    response = await client.post(
        f"{ollama_url.rstrip('/')}/api/pull",
        json={"name": model, "stream": False},
        timeout=timeout_seconds,
    )
    response.raise_for_status()


async def ensure_profile_models(
    client: httpx.AsyncClient,
    *,
    ollama_url: str,
    policy: OllamaRuntimePolicy,
    pull: bool = True,
) -> tuple[list[str], list[str], list[str]]:
    installed = await list_ollama_models(client, ollama_url=ollama_url)
    wanted = models_to_warm(policy)
    missing = [name for name in wanted if not model_is_available(name, installed)]
    if not pull or not missing:
        return installed, missing, []

    pulled: list[str] = []
    for name in missing:
        try:
            await pull_ollama_model(client, ollama_url=ollama_url, model=name)
            pulled.append(name)
        except httpx.HTTPError:
            continue
    if pulled:
        installed = await list_ollama_models(client, ollama_url=ollama_url)
    still_missing = [name for name in wanted if not model_is_available(name, installed)]
    return installed, still_missing, pulled
