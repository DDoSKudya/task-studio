from __future__ import annotations

import uuid

import httpx
from app.config import SearchSettings
from app.domain.indexing import index_external_course, index_pack_version, unindex_pack
from meilisearch.client import Client


async def handle_index_payload(
    payload: dict[str, object],
    *,
    meili: Client,
    http_client: httpx.AsyncClient,
    settings: SearchSettings,
) -> None:
    op = str(payload.get("op", "upsert"))
    user_id = uuid.UUID(str(payload["user_id"]))
    if op == "upsert_external":
        await index_external_course(
            meili,
            settings,
            user_id=user_id,
            platform=str(payload["platform"]),
            external_id=str(payload["external_id"]),
            title=str(payload["title"]),
            description=str(payload.get("description", "")),
        )
        return
    if op == "delete_pack":
        pack_id = uuid.UUID(str(payload["pack_id"]))
        raw_versions = payload.get("pack_version_ids") or []
        version_items: list[object] = raw_versions if isinstance(raw_versions, list) else []
        version_ids = [
            uuid.UUID(str(item)) for item in version_items if isinstance(item, str | uuid.UUID)
        ]
        unindex_pack(
            meili,
            settings,
            user_id=user_id,
            pack_id=pack_id,
            pack_version_ids=version_ids,
        )
        return

    pack_version_id = uuid.UUID(str(payload["pack_version_id"]))
    rank_raw = payload.get("rank_tier", 1)
    rank_tier = int(rank_raw) if isinstance(rank_raw, int) else 1
    await index_pack_version(
        meili,
        http_client,
        settings,
        user_id=user_id,
        pack_version_id=pack_version_id,
        rank_tier=rank_tier,
    )
