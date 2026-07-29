from __future__ import annotations

import uuid

from app.domain.documents import manifest_source, search_document, step_documents


def pack_version_documents(
    manifest: dict[str, object],
    *,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
    pack_version_id: uuid.UUID,
    pack_title: str,
    rank_tier: int,
) -> list[dict[str, object]]:
    title = str(manifest.get("title", pack_title))
    source = manifest_source(manifest)
    platform = source if source != "local" else None
    pack_id_s = str(pack_id)
    version_id = str(pack_version_id)
    return [
        search_document(
            doc_id=f"course:{pack_version_id}",
            kind="course",
            user_id=user_id,
            title=title,
            content=title,
            source=source,
            platform=platform,
            pack_id=pack_id_s,
            pack_version_id=version_id,
            rank_tier=rank_tier,
        ),
        *step_documents(
            manifest,
            user_id=user_id,
            source=source,
            platform=platform,
            pack_id=pack_id_s,
            pack_version_id=version_id,
            rank_tier=rank_tier,
        ),
    ]
