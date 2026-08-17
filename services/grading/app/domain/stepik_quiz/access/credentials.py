from __future__ import annotations

import os
from uuid import UUID

import httpx
from studio_common.secrets.secrets_settings import decrypt_platform_credentials


async def fetch_stepik_credentials(
    client: httpx.AsyncClient,
    *,
    auth_service_url: str,
    user_id: UUID | None,
) -> dict[str, str]:
    if not auth_service_url or user_id is None:
        return {}
    try:
        response = await client.get(
            f"{auth_service_url.rstrip('/')}/internal/v1/auth/me",
            headers={"X-User-Id": str(user_id)},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return {}
    payload = response.json()
    settings = payload.get("settings") if isinstance(payload, dict) else None
    if not isinstance(settings, dict):
        return {}
    integrations = settings.get("integrations")
    if not isinstance(integrations, dict):
        return {}
    platform = integrations.get("stepik")
    if not isinstance(platform, dict):
        return {}
    master = os.getenv("SECRETS_MASTER_KEY") or None
    return decrypt_platform_credentials(platform, master_key=master)
