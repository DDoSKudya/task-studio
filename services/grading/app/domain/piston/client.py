                                                        

from __future__ import annotations

import httpx
from app.config import GradingSettings
from app.domain.check.outcome import GradingError
from app.domain.harness import PistonJob
from app.domain.piston.lang import map_piston_language, piston_entry_name
from app.domain.piston.response import (
    parse_piston_response,
    piston_client_error,
    piston_outcome,
)

__all__ = [
    "execute_piston",
    "execute_piston_job",
    "parse_piston_response",
    "piston_client_error",
    "piston_outcome",
]


async def execute_piston_job(
    client: httpx.AsyncClient,
    *,
    settings: GradingSettings,
    job: PistonJob,
) -> dict[str, object]:
    return await execute_piston(
        client,
        settings=settings,
        language=job.language,
        version=job.version,
        files=job.files,
        args=job.args,
    )


async def execute_piston(
    client: httpx.AsyncClient,
    *,
    settings: GradingSettings,
    language: str,
    version: str,
    source: str | None = None,
    files: list[dict[str, str]] | None = None,
    args: list[str] | None = None,
) -> dict[str, object]:
    mapped_language, mapped_version = map_piston_language(language, version)
    if files:
        payload_files = files
    else:
        content = source if isinstance(source, str) else ""
        payload_files = [
            {
                "name": piston_entry_name(language, mapped_language),
                "content": content,
            }
        ]
    payload: dict[str, object] = {
        "language": mapped_language,
        "version": mapped_version,
        "files": payload_files,
        "run_timeout": int(settings.piston_timeout_seconds * 1000),
    }
    if args:
        payload["args"] = args
    try:
        response = await client.post(
            f"{settings.piston_url}/api/v2/execute",
            json=payload,
            timeout=settings.piston_timeout_seconds + 2,
        )
    except httpx.HTTPError as exc:
        raise GradingError(503, "code runner unavailable") from exc

    if response.status_code >= 500:
        raise GradingError(503, "code runner failed")
    if response.status_code >= 400:
        raise GradingError(502, piston_client_error(response))

    return parse_piston_response(response.json())
