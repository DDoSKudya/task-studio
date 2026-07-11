from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, cast, get_args

from pydantic import BaseModel, ConfigDict, Field

ImportJobStatus = Literal[
    "pending",
    "fetching",
    "normalizing",
    "building",
    "done",
    "failed",
]


_KNOWN_JOB_STATUSES = frozenset(get_args(ImportJobStatus))


def parse_job_status(status: str) -> ImportJobStatus:
    if status in _KNOWN_JOB_STATUSES:
        return cast(ImportJobStatus, status)
    return "failed"


class ImportWarning(BaseModel):
    model_config = ConfigDict(strict=True)

    step: str
    reason: str


class ImportReport(BaseModel):
    model_config = ConfigDict(strict=True)

    total_items: int = Field(ge=0)
    imported_full: int = Field(ge=0)
    imported_partial: int = Field(ge=0)
    skipped: int = Field(ge=0)
    warnings: list[ImportWarning] = Field(default_factory=list)
    fidelity_percent: float = Field(default=0.0, ge=0, le=100)


class AdapterCapabilities(BaseModel):
    model_config = ConfigDict(strict=True)

    import_course: bool = False
    search_catalog: bool = False
    requires_auth: bool = False
    content_types: list[str] = Field(default_factory=list)


class AdapterInfo(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    version: str
    display_name: str
    capabilities: AdapterCapabilities


class ExternalCourseSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    platform: str
    external_id: str
    title: str
    description: str = ""


class StartImportRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    course_id: str = Field(min_length=1)


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    platform_id: str
    external_course_id: str
    status: ImportJobStatus
    pack_version_id: uuid.UUID | None = None
    error: str | None = None
    report: ImportReport | None = None
    created_at: datetime
