from __future__ import annotations

import uuid


def manifest_source(manifest: dict[str, object]) -> str:
    source_obj = manifest.get("source")
    if isinstance(source_obj, dict) and isinstance(source_obj.get("type"), str):
        return source_obj["type"]
    return "local"


def step_documents(
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
            search_document(
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


def search_document(
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
