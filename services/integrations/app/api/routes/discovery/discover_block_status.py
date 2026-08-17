from __future__ import annotations

from app.api.routes.discovery.discover_summaries import course_summary_from_raw
from studio_contracts.api.integration_schemas import ExternalCourseSummary, PlatformCatalogStatus
from studio_integration_sdk.registry import AdapterModule


def credentials_complete(adapter: AdapterModule, credentials: dict[str, str]) -> bool:
    if not adapter.info.capabilities.requires_auth:
        return True
    auth = adapter.info.auth
    if auth is None or not auth.settings_fields:
        return False
    return all(credentials.get(field, "").strip() for field in auth.settings_fields)


def resolve_platform_catalog_state(
    adapter: AdapterModule,
    *,
    credentials: dict[str, str],
    error: str | None,
    remote: list[dict[str, object]] | None,
) -> tuple[PlatformCatalogStatus, str | None, list[ExternalCourseSummary]]:
    info = adapter.info
    platform_id = info.id
    supports_catalog = info.capabilities.search_catalog or info.capabilities.import_course

    if not supports_catalog:
        return "unavailable", "import not supported", []
    if not info.capabilities.search_catalog and info.capabilities.import_course:
        return "upload_only", "upload archive in settings", []
    if (
        info.capabilities.requires_auth
        and not credentials_complete(adapter, credentials)
        and not info.capabilities.import_without_auth
    ):
        return "needs_auth", "credentials required in settings", []
    if info.capabilities.requires_auth and not credentials_complete(adapter, credentials):
        if error:
            return "error", error, []
        return (
            "ready",
            "import public courses by ID; save credentials to sync enrolled",
            [],
        )
    if error:
        return "error", error, []

    parsed: list[ExternalCourseSummary] = []
    for raw in remote or []:
        if not isinstance(raw, dict):
            continue
        try:
            summary = course_summary_from_raw(raw, platform_id=platform_id)
        except (TypeError, ValueError):
            continue
        if summary is not None:
            parsed.append(summary)
    if parsed:
        return "ready", None, parsed
    return "empty", "no courses available for this account or platform", parsed
