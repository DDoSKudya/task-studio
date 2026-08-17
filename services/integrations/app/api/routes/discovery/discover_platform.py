from __future__ import annotations

import uuid

import httpx
from app.api.routes.common.helpers import credentials_complete, platform_block_from_fetch
from app.api.routes.discovery.discover_cache import cached_or_error_block
from app.api.routes.discovery.discover_platform_remote import fetch_and_sync_platform_block
from app.config import IntegrationsSettings
from app.domain.credentials import fetch_platform_credentials
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.integration_schemas import PlatformCatalogBlock
from studio_integration_sdk.registry import AdapterModule

_cached_or_error_block = cached_or_error_block


async def discover_platform_block(
    *,
    session: AsyncSession,
    settings: IntegrationsSettings,
    client: httpx.AsyncClient,
    user_id: uuid.UUID,
    platform_id: str,
    adapter: AdapterModule,
    needle: str,
) -> PlatformCatalogBlock | None:
    info = adapter.info
    if not (info.capabilities.search_catalog or info.capabilities.import_course):
        return None

    credentials = await fetch_platform_credentials(
        client,
        auth_service_url=settings.auth_service_url,
        user_id=user_id,
        platform_id=platform_id,
    )

    if not info.capabilities.search_catalog and info.capabilities.import_course:
        return platform_block_from_fetch(adapter, credentials=credentials, needle=needle)

    needs_login = (
        info.capabilities.requires_auth
        and not credentials_complete(adapter, credentials)
        and not info.capabilities.import_without_auth
    )
    if needs_login:
        return platform_block_from_fetch(adapter, credentials=credentials, needle=needle)

    try:
        return await fetch_and_sync_platform_block(
            session=session,
            settings=settings,
            user_id=user_id,
            platform_id=platform_id,
            adapter=adapter,
            credentials=credentials,
            needle=needle,
        )
    except ValueError as exc:
        return await cached_or_error_block(
            session,
            user_id=user_id,
            platform_id=platform_id,
            adapter=adapter,
            credentials=credentials,
            needle=needle,
            ready_message=f"cached catalog ({exc})",
            error=str(exc),
        )
    except (TypeError, KeyError, OSError, RuntimeError, httpx.HTTPError) as exc:
        return await cached_or_error_block(
            session,
            user_id=user_id,
            platform_id=platform_id,
            adapter=adapter,
            credentials=credentials,
            needle=needle,
            ready_message="showing cached catalog after upstream error",
            error=str(exc).strip() or exc.__class__.__name__,
        )
