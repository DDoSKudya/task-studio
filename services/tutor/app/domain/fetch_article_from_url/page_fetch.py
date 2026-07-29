from __future__ import annotations

from urllib.parse import urljoin

import httpx
from app.domain.errors import TutorError
from fastapi import status

from .url import (
    _BROWSER_HEADERS,
    _FETCH_TIMEOUT,
    _MAX_RAW_CHARS,
    _MAX_REDIRECTS,
    validate_public_http_url,
)


async def fetch_page(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        validate_public_http_url(current)
        try:
            response = await client.get(
                current,
                headers=_BROWSER_HEADERS,
                follow_redirects=False,
                timeout=_FETCH_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise TutorError(status.HTTP_502_BAD_GATEWAY, "failed to fetch url") from exc

        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise TutorError(status.HTTP_502_BAD_GATEWAY, "redirect without location")
            current = urljoin(current, location)
            continue

        if response.status_code >= 400:
            raise TutorError(
                status.HTTP_502_BAD_GATEWAY,
                f"url returned HTTP {response.status_code}",
            )

        content_type = (response.headers.get("content-type") or "").lower()
        raw = response.text
        if len(raw) > _MAX_RAW_CHARS:
            raw = raw[:_MAX_RAW_CHARS]
        return content_type, raw

    raise TutorError(status.HTTP_502_BAD_GATEWAY, "too many redirects")
