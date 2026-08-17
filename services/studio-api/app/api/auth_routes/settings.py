from __future__ import annotations

import httpx
from app.config import StudioApiSettings
from studio_common.secrets.secrets_settings import merge_integrations_settings, merge_tutor_settings
from studio_common.security.auth_schemas import SettingsPatch


async def prepare_settings_patch(
    body: SettingsPatch,
    settings: StudioApiSettings,
    *,
    client: httpx.AsyncClient,
    user_id: str,
) -> dict[str, object]:
    payload = body.model_dump(mode="json", exclude_unset=True)
    settings_blob = payload.get("settings")
    if not isinstance(settings_blob, dict):
        return payload

    existing = await load_existing_settings(client, settings, user_id=user_id)
    master_key = settings.secrets_master_key

    tutor = settings_blob.get("tutor")
    if isinstance(tutor, dict):
        prev_tutor = existing.get("tutor")
        settings_blob["tutor"] = merge_tutor_settings(
            dict(tutor),
            prev_tutor if isinstance(prev_tutor, dict) else None,
            master_key=master_key,
        )

    integrations = settings_blob.get("integrations")
    if isinstance(integrations, dict):
        prev_integrations = existing.get("integrations")
        settings_blob["integrations"] = merge_integrations_settings(
            dict(integrations),
            prev_integrations if isinstance(prev_integrations, dict) else None,
            master_key=master_key,
        )

    payload["settings"] = settings_blob
    return payload


async def load_existing_settings(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    *,
    user_id: str,
) -> dict[str, object]:
    try:
        upstream = await client.get(
            f"{settings.auth_service_url}/internal/v1/auth/me",
            headers={"X-User-Id": user_id},
        )
        upstream.raise_for_status()
    except httpx.HTTPError:
        return {}
    try:
        body = upstream.json()
    except ValueError:
        return {}
    if not isinstance(body, dict):
        return {}
    blob = body.get("settings")
    return dict(blob) if isinstance(blob, dict) else {}
