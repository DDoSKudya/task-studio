from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchSettings:
    meilisearch_url: str
    meilisearch_key: str | None
    catalog_service_url: str
    rabbitmq_url: str
    search_index_queue: str
    ollama_url: str
    index_name: str


def load_settings() -> SearchSettings:
    return SearchSettings(
        meilisearch_url=os.getenv("MEILISEARCH_URL", "http://meilisearch:7700").rstrip("/"),
        meilisearch_key=os.getenv("MEILISEARCH_KEY") or None,
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "").strip(),
        search_index_queue=os.getenv("SEARCH_INDEX_QUEUE", "search.index"),
        ollama_url=os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/"),
        index_name=os.getenv("SEARCH_INDEX_NAME", "studio"),
    )
