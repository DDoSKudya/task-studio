from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger("orchestrator.ollama_probe")


async def ollama_is_busy(client: httpx.AsyncClient, ollama_url: str) -> bool:

    base = ollama_url.rstrip("/")
    if not base:
        return False
    try:
        response = await client.get(f"{base}/api/ps", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        log.debug("ollama_ps_probe_failed", error=str(exc))
        return False
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return False
    return len(models) > 0
