from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GradingCheckRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    step: dict[str, object]
    submission: dict[str, object]


class GradingCheckResponse(BaseModel):
    passed: bool
    score: float
    feedback: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class GradingLabSubmitRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    step: dict[str, object]
    submission: dict[str, object]
    user_id: str
    pack_version_id: str


class GradingLabSubmitResponse(BaseModel):
    status: Literal["pending"]
    attempt_id: str


class GradingLabCompleteRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    attempt_id: str
    passed: bool
    score: float
    feedback: str | None = None
    details: dict[str, object] = Field(default_factory=dict)
    duration_ms: int = 0
