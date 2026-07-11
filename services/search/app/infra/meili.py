from __future__ import annotations

import contextlib

import meilisearch
from app.config import SearchSettings
from meilisearch.client import Client
from meilisearch.errors import MeilisearchApiError
from meilisearch.index import Index


def meili_client(settings: SearchSettings) -> Client:
    return meilisearch.Client(settings.meilisearch_url, settings.meilisearch_key)


def ensure_index(client: Client, index_name: str, *, ollama_url: str) -> None:
    client.create_index(index_name, {"primaryKey": "id"})
    index = client.index(index_name)
    index.update_filterable_attributes(
        ["user_id", "kind", "source", "platform", "rank_tier", "pack_id"]
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
