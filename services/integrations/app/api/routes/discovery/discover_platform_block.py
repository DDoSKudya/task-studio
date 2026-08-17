from __future__ import annotations

from app.api.routes.discovery.discover_block_status import (
    credentials_complete,
    resolve_platform_catalog_state,
)
from studio_contracts.api.integration_schemas import PlatformCatalogBlock
from studio_integration_sdk.registry import AdapterModule

__all__ = [
    "credentials_complete",
    "fetch_remote_courses",
    "platform_block_from_fetch",
]


def fetch_remote_courses(
    adapter: AdapterModule,
    *,
    credentials: dict[str, str],
    needle: str,
) -> list[dict[str, object]]:
    kwargs = credentials
    if needle:
        return adapter.search_remote(query=needle, **kwargs)
    return adapter.list_catalog(**kwargs)


def platform_block_from_fetch(
    adapter: AdapterModule,
    *,
    credentials: dict[str, str],
    needle: str,
    error: str | None = None,
    remote: list[dict[str, object]] | None = None,
) -> PlatformCatalogBlock:
    _ = needle
    info = adapter.info
    supports_catalog = info.capabilities.search_catalog or info.capabilities.import_course
    status, message, courses = resolve_platform_catalog_state(
        adapter,
        credentials=credentials,
        error=error,
        remote=remote,
    )
    return PlatformCatalogBlock(
        platform_id=info.id,
        display_name=info.display_name,
        requires_auth=info.capabilities.requires_auth,
        supports_catalog=supports_catalog,
        status=status,
        message=message,
        course_count=len(courses),
        courses=courses,
    )
