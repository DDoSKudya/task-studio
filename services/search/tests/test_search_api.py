from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(build_app) -> None:
    app = build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_documents_maps_meili_hits() -> None:
    from app.config import SearchSettings
    from app.domain.query import search_documents

    user_id = uuid.uuid4()
    index = MagicMock()
    index.search.return_value = {
        "hits": [
            {
                "id": "pack:1",
                "title": "Docker",
                "description": "containers",
                "source": "local",
                "rank_tier": 1,
                "pack_id": str(uuid.uuid4()),
                "_rankingScore": 0.91,
            }
        ]
    }
    client = MagicMock()
    client.index.return_value = index
    settings = SearchSettings(
        meilisearch_url="http://meili.test",
        meilisearch_key=None,
        catalog_service_url="http://catalog.test",
        rabbitmq_url="",
        search_index_queue="search.index",
        ollama_url="http://ollama.test",
        index_name="studio",
    )

    result = search_documents(
        client,
        settings,
        user_id=user_id,
        query="docker",
        limit=10,
    )

    assert result.query == "docker"
    assert result.total == 1
    assert result.hits[0].title == "Docker"
    assert result.hits[0].kind == "installed"
    index.search.assert_called()
    filter_arg = index.search.call_args.args[1]["filter"]
    assert f'user_id = "{user_id}"' in filter_arg


def test_unindex_pack_deletes_by_user_and_pack() -> None:
    from app.config import SearchSettings
    from app.domain.indexing import unindex_pack

    user_id = uuid.uuid4()
    pack_id = uuid.uuid4()
    version_id = uuid.uuid4()
    index = MagicMock()
    client = MagicMock()
    client.index.return_value = index
    settings = SearchSettings(
        meilisearch_url="http://meili.test",
        meilisearch_key=None,
        catalog_service_url="http://catalog.test",
        rabbitmq_url="",
        search_index_queue="search.index",
        ollama_url="http://ollama.test",
        index_name="studio",
    )

    unindex_pack(
        client,
        settings,
        user_id=user_id,
        pack_id=pack_id,
        pack_version_ids=[version_id],
    )

    assert index.delete_documents.call_count == 2
    first_filter = index.delete_documents.call_args_list[0].kwargs["filter"]
    assert f'pack_id = "{pack_id}"' in first_filter
    assert f'user_id = "{user_id}"' in first_filter


@pytest.mark.asyncio
async def test_search_endpoint_uses_meili_mock(build_app) -> None:
    app = build_app()
    index = MagicMock()
    index.search.return_value = {
        "hits": [
            {
                "id": "ext:1",
                "title": "Python",
                "description": "",
                "source": "stepik",
                "rank_tier": 3,
                "_rankingScore": 0.4,
            }
        ]
    }
    mock_client = MagicMock()
    mock_client.index.return_value = index
    app.state.meili_client = mock_client

    user_id = "11111111-1111-1111-1111-111111111111"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/internal/v1/search",
            params={"q": "python"},
            headers={"X-User-Id": user_id},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["hits"][0]["kind"] == "external"
