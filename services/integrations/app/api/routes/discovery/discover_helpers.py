from __future__ import annotations

import httpx
from app.api.routes.discovery.discover_platform_block import (
    credentials_complete,
    fetch_remote_courses,
    platform_block_from_fetch,
)
from app.api.routes.discovery.discover_summaries import (
    course_summary_from_raw,
    filter_summaries,
    is_demo_course,
    summaries_from_cache,
    to_course_summary,
)
from fastapi import HTTPException, Request, status
from studio_integration_sdk.registry import AdapterModule

__all__ = [
    "http_client",
    "require_adapter",
    "to_course_summary",
    "is_demo_course",
    "summaries_from_cache",
    "credentials_complete",
    "fetch_remote_courses",
    "course_summary_from_raw",
    "platform_block_from_fetch",
    "filter_summaries",
]


def http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def require_adapter(adapters: dict[str, AdapterModule], platform_id: str) -> AdapterModule:
    adapter = adapters.get(platform_id)
    if adapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="platform not found")
    return adapter
