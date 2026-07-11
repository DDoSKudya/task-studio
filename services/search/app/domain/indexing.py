from __future__ import annotations

import uuid

import httpx
from app.config import SearchSettings
from meilisearch.client import Client
from studio_contracts.catalog_schemas import PackVersionContext


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
    manifest = context.manifest
    title = str(manifest.get("title", context.pack_title))
    source = _manifest_source(manifest)
    platform = source if source != "local" else None
    pack_id = str(context.pack_id)
    version_id = str(pack_version_id)

    documents = [
        _document(
            doc_id=f"course:{pack_version_id}",
            kind="course",
            user_id=user_id,
            title=title,
            content=title,
            source=source,
            platform=platform,
            pack_id=pack_id,
            pack_version_id=version_id,
            rank_tier=rank_tier,
        ),
        *_step_documents(
            manifest,
            user_id=user_id,
            source=source,
            platform=platform,
            pack_id=pack_id,
            pack_version_id=version_id,
            rank_tier=rank_tier,
        ),
    ]
    client.index(settings.index_name).add_documents(documents)


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
    document = _document(
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


async def _fetch_pack_context(
    http: httpx.AsyncClient,
    settings: SearchSettings,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> PackVersionContext:
    response = await http.get(
        f"{settings.catalog_service_url}/internal/v1/catalog/pack-versions/{pack_version_id}",
        headers={"X-User-Id": str(user_id)},
    )
    response.raise_for_status()
    return PackVersionContext.model_validate(response.json())


def _manifest_source(manifest: dict[str, object]) -> str:
    source_obj = manifest.get("source")
    if isinstance(source_obj, dict) and isinstance(source_obj.get("type"), str):
        return source_obj["type"]
    return "local"


def _step_documents(
    manifest: dict[str, object],
    *,
    user_id: uuid.UUID,
    source: str,
    platform: str | None,
    pack_id: str,
    pack_version_id: str,
    rank_tier: int,
) -> list[dict[str, object]]:
    steps = manifest.get("steps")
    if not isinstance(steps, dict):
        return []

    documents: list[dict[str, object]] = []
    for step_id, step in steps.items():
        if not isinstance(step, dict):
            continue
        step_title = step.get("title")
        if not isinstance(step_title, str):
            continue
        content = step.get("content")
        documents.append(
            _document(
                doc_id=f"step:{pack_version_id}:{step_id}",
                kind="step",
                user_id=user_id,
                title=step_title,
                content=content if isinstance(content, str) else step_title,
                source=source,
                platform=platform,
                pack_id=pack_id,
                pack_version_id=pack_version_id,
                rank_tier=rank_tier,
            )
        )
    return documents


def _document(
    *,
    doc_id: str,
    kind: str,
    user_id: uuid.UUID,
    title: str,
    content: str,
    source: str,
    rank_tier: int,
    platform: str | None = None,
    description: str = "",
    pack_id: str | None = None,
    pack_version_id: str | None = None,
    external_id: str | None = None,
) -> dict[str, object]:
    return {
        "id": doc_id,
        "kind": kind,
        "user_id": str(user_id),
        "title": title,
        "description": description,
        "content": content,
        "source": source,
        "platform": platform,
        "pack_id": pack_id,
        "pack_version_id": pack_version_id,
        "external_id": external_id,
        "rank_tier": rank_tier,
    }
