from __future__ import annotations

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
