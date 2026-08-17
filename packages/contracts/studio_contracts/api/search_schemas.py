from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchResultKind = Literal["installed", "uploaded", "external"]
SearchType = Literal["course", "step"]


class SearchHit(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    kind: SearchResultKind
    title: str
    description: str = ""
    source: str
    platform: str | None = None
    external_id: str | None = None
    pack_id: str | None = None
    pack_version_id: str | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    query: str
    hits: list[SearchHit]
    total: int


class SearchImportRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    platform: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    force: bool = False
