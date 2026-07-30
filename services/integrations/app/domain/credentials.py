from __future__ import annotations

import os
import uuid

import httpx
from studio_common.secrets_settings import decrypt_platform_credentials


async def fetch_platform_credentials(
    client: httpx.AsyncClient,
    *,
    auth_service_url: str,
    user_id: uuid.UUID,
    platform_id: str,
    secrets_master_key: str | None = None,
) -> dict[str, str]:

    if not auth_service_url:
        return {}
    try:
        response = await client.get(
            f"{auth_service_url}/internal/v1/auth/me",
            headers={"X-User-Id": str(user_id)},
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return {}
    payload = response.json()
    settings = payload.get("settings")
    if not isinstance(settings, dict):
        return {}
    integrations = settings.get("integrations")
    if not isinstance(integrations, dict):
        return {}
    platform = integrations.get(platform_id)
    if not isinstance(platform, dict):
        return {}
    master = secrets_master_key or os.getenv("SECRETS_MASTER_KEY") or None
    return decrypt_platform_credentials(platform, master_key=master)
