from __future__ import annotations

import uuid

from app.config import SearchSettings
from meilisearch.client import Client
from meilisearch.errors import MeilisearchApiError
from studio_contracts.api.search_schemas import (
    SearchHit,
    SearchResponse,
    SearchResultKind,
    SearchType,
)


def search_documents(
    client: Client,
    settings: SearchSettings,
    *,
    user_id: uuid.UUID,
    query: str,
    search_type: SearchType | None = None,
    limit: int = 20,
) -> SearchResponse:
    index = client.index(settings.index_name)
    filters = [f'user_id = "{user_id}"']
    if search_type is not None:
        filters.append(f'kind = "{search_type}"')

    search_options: dict[str, object] = {
        "filter": " AND ".join(filters),
        "limit": limit,
        "sort": ["rank_tier:asc"],
    }
    try:
        result = index.search(
            query,
            {
                **search_options,
                "hybrid": {"semanticRatio": 0.5, "embedder": "ollama"},
            },
        )
    except MeilisearchApiError:
        result = index.search(query, search_options)

    hits = [hit for raw in result.get("hits", []) if (hit := _parse_hit(raw)) is not None]
    return SearchResponse(query=query, hits=hits, total=len(hits))


def _parse_hit(raw: object) -> SearchHit | None:
    if not isinstance(raw, dict):
        return None
    rank_tier = raw.get("rank_tier", 3)
    tier = int(rank_tier) if isinstance(rank_tier, int) else 3
    return SearchHit(
        id=str(raw.get("id", "")),
        kind=_rank_label(tier),
        title=str(raw.get("title", "")),
        description=str(raw.get("description", "")),
        source=str(raw.get("source", "")),
        platform=_optional_str(raw, "platform"),
        external_id=_optional_str(raw, "external_id"),
        pack_id=_optional_str(raw, "pack_id"),
        pack_version_id=_optional_str(raw, "pack_version_id"),
        score=float(raw.get("_rankingScore", 0.0) or 0.0),
    )


def _optional_str(raw: dict[str, object], key: str) -> str | None:
    value = raw.get(key)
    return str(value) if value is not None else None


def _rank_label(rank_tier: int) -> SearchResultKind:
    if rank_tier <= 1:
        return "installed"
    if rank_tier == 2:
        return "uploaded"
    return "external"
