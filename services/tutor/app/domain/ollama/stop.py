from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


async def stop_ollama_model(
    client: httpx.AsyncClient,
    *,
    ollama_url: str,
    model: str,
) -> None:

    base = ollama_url.rstrip("/")
    name = model.strip()
    if not base or not name:
        return
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
    try:
        response = await client.post(
            f"{base}/api/generate",
            json={"model": name, "prompt": "", "keep_alive": 0},
            timeout=timeout,
        )
        response.raise_for_status()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.info("ollama stop skipped for %s: %s", name, exc)
