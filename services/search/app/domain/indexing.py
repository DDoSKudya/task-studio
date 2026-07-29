from __future__ import annotations

import uuid

import httpx
from app.config import SearchSettings
from app.domain.documents import search_document
from app.domain.indexing_docs import pack_version_documents
from app.domain.indexing_fetch import fetch_pack_context
from meilisearch.client import Client

_fetch_pack_context = fetch_pack_context


async def index_pack_version(
    client: Client,
    http: httpx.AsyncClient,
    settings: SearchSettings,
    *,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
    rank_tier: int = 1,
) -> None:
    context = await _fetch_pack_context(http, settings, user_id, pack_version_id)
    documents = pack_version_documents(
        context.manifest,
        user_id=user_id,
        pack_id=context.pack_id,
        pack_version_id=pack_version_id,
        pack_title=context.pack_title,
        rank_tier=rank_tier,
    )
    client.index(settings.index_name).add_documents(documents)


def unindex_pack(
    client: Client,
    settings: SearchSettings,
    *,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    pack_version_ids: list[uuid.UUID] | None = None,
) -> None:
    index = client.index(settings.index_name)
    filters = [f'user_id = "{user_id}"', f'pack_id = "{pack_id}"']
    index.delete_documents(filter=" AND ".join(filters))
    if pack_version_ids:
        for version_id in pack_version_ids:
            index.delete_documents(
                filter=f'user_id = "{user_id}" AND pack_version_id = "{version_id}"'
            )


async def index_external_course(
    client: Client,
    settings: SearchSettings,
    *,
    user_id: uuid.UUID,
    platform: str,
    external_id: str,
    title: str,
    description: str = "",
) -> None:
    document = search_document(
        doc_id=f"external:{platform}:{external_id}:{user_id}",
        kind="course",
        user_id=user_id,
        title=title,
        content=f"{title} {description}".strip(),
        description=description,
        source=platform,
        platform=platform,
        external_id=external_id,
        rank_tier=3,
    )
    client.index(settings.index_name).add_documents([document])
