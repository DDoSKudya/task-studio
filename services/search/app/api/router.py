from __future__ import annotations

import uuid
from typing import Annotated

from app.api.deps import MeiliClient, Settings
from app.domain.indexing import unindex_pack
from app.domain.query import search_documents
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from studio_common.internal import InternalUserId
from studio_contracts.search_schemas import SearchResponse, SearchType

router = APIRouter(prefix="/internal/v1/search", tags=["search"])


class UnindexPackRequest(BaseModel):
                                                                                            
    model_config = ConfigDict(strict=False)

    pack_id: uuid.UUID
    pack_version_ids: list[uuid.UUID] = Field(default_factory=list)


@router.get("", response_model=SearchResponse)
async def search(
    q: Annotated[str, Query(min_length=1)],
    user_id: InternalUserId,
    client: MeiliClient,
    settings: Settings,
    type: Annotated[SearchType | None, Query(alias="type")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    return search_documents(
        client,
        settings,
        user_id=user_id,
        query=q,
        search_type=type,
        limit=limit,
    )


@router.post("/unindex-pack")
async def unindex_pack_endpoint(
    body: UnindexPackRequest,
    user_id: InternalUserId,
    client: MeiliClient,
    settings: Settings,
) -> dict[str, str]:
    unindex_pack(
        client,
        settings,
        user_id=user_id,
        pack_id=body.pack_id,
        pack_version_ids=body.pack_version_ids,
    )
    return {"status": "ok"}
