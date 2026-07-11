from __future__ import annotations

from typing import Annotated

from app.api.deps import MeiliClient, Settings
from app.domain.query import search_documents
from fastapi import APIRouter, Query
from studio_common.internal import InternalUserId
from studio_contracts.search_schemas import SearchResponse, SearchType

router = APIRouter(prefix="/internal/v1/search", tags=["search"])


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
