from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PackIntegrityStatus = Literal["ok", "broken"]


class PackSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    source: str
    external_id: str | None = None
    version: str
    version_id: uuid.UUID
    installed_at: datetime
    integrity: PackIntegrityStatus = "ok"
    integrity_issues: list[str] = Field(default_factory=list)


class PackVersionInfo(BaseModel):
    id: uuid.UUID
    version: str
    created_at: datetime
    active: bool


class PackVersionContext(BaseModel):
    id: uuid.UUID
    pack_id: uuid.UUID
    pack_title: str
    version: str
    manifest: dict[str, object]
    disk_path: str
    object_key: str | None = None


class PackDetail(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    source: str
    external_id: str | None = None
    schema_version: int
    active_version: PackVersionInfo
    versions: list[PackVersionInfo]
    manifest: dict[str, object]
    integrity: PackIntegrityStatus = "ok"
    integrity_issues: list[str] = Field(default_factory=list)


class PackUploadResponse(BaseModel):
    pack_id: uuid.UUID
    version_id: uuid.UUID
    slug: str
    title: str
    version: str


class ActivatePackRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    version: str = Field(min_length=1, max_length=64)


class RegisterImportedPackRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    manifest: dict[str, object]
    disk_path: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    import_report: dict[str, object] | None = None
    object_key: str | None = None
