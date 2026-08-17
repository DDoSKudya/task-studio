from __future__ import annotations

import contextlib

import httpx
import meilisearch
from app.config import SearchSettings
from meilisearch.client import Client
from meilisearch.errors import MeilisearchApiError
from meilisearch.index import Index


def meili_client(settings: SearchSettings) -> Client:
    client = meilisearch.Client(settings.meilisearch_url, settings.meilisearch_key)
    if settings.meilisearch_key:
        return client
    _strip_auth_header(client.http)
    original_index = client.index

    def index(name: str) -> Index:
        idx = original_index(name)
        _strip_auth_header(idx.http)
        return idx

    client.index = index  # type: ignore[method-assign]
    return client


def _strip_auth_header(http: object) -> None:
    headers = getattr(http, "headers", None)
    if isinstance(headers, dict):
        headers.pop("Authorization", None)


def _index_exists(client: Client, index_name: str) -> bool:
    try:
        payload = client.get_indexes()
    except MeilisearchApiError:
        return False
    results = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(results, list):
        return False
    return any(getattr(item, "uid", None) == index_name for item in results)


def _create_index_http(base_url: str, index_name: str) -> None:
    response = httpx.post(
        f"{base_url.rstrip('/')}/indexes",
        json={"uid": index_name, "primaryKey": "id"},
        timeout=30.0,
    )
    if response.status_code in {201, 202}:
        return
    if response.status_code == 409:
        return
    response.raise_for_status()


def ensure_index(client: Client, index_name: str, *, ollama_url: str) -> None:
    if not _index_exists(client, index_name):
        if client.config.api_key:
            client.create_index(index_name, {"primaryKey": "id"})
        else:
            _create_index_http(client.config.url, index_name)
    index = client.index(index_name)
    index.update_filterable_attributes(
        ["user_id", "kind", "source", "platform", "rank_tier", "pack_id", "pack_version_id"]
    )
    index.update_sortable_attributes(["rank_tier"])
    index.update_searchable_attributes(["title", "description", "content"])
    _configure_hybrid(index, ollama_url)


def _configure_hybrid(index: Index, ollama_url: str) -> None:
    with contextlib.suppress(MeilisearchApiError):
        index.update_embedders(
            {
                "ollama": {
                    "source": "ollama",
                    "url": f"{ollama_url}/api/embeddings",
                    "model": "nomic-embed-text",
                    "documentTemplate": "{{doc.title}} {{doc.description}} {{doc.content}}",
                }
            }
        )
