from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PackSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    source: str
    version: str
    version_id: uuid.UUID
    installed_at: datetime


class PackVersionInfo(BaseModel):
    id: uuid.UUID
    version: str
    created_at: datetime
    active: bool


class PackDetail(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    source: str
    schema_version: int
    active_version: PackVersionInfo
    versions: list[PackVersionInfo]
    manifest: dict[str, object]


class PackUploadResponse(BaseModel):
    pack_id: uuid.UUID
    version_id: uuid.UUID
    slug: str
    title: str
    version: str


class ActivatePackRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    version: str = Field(min_length=1, max_length=64)
