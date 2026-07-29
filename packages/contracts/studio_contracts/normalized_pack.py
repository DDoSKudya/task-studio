from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StepKind = Literal["theory", "video", "quiz", "code", "lab", "task"]
StepPhase = Literal["study", "practice", "assess"]
StepFidelity = Literal["full", "partial"]


class NormalizedStep(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str = Field(min_length=1)
    kind: StepKind
    title: str = Field(min_length=1)
    phase: StepPhase
    payload: dict[str, object] = Field(default_factory=dict)
    fidelity: StepFidelity = "full"


class NormalizedTopic(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    study: list[str] = Field(default_factory=list)
    practice: list[str] = Field(default_factory=list)
    assess: list[str] = Field(default_factory=list)


class NormalizedPack(BaseModel):
    model_config = ConfigDict(strict=True)

    platform: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    version: str = Field(min_length=1)
    locale: str = "en"
    topics: list[NormalizedTopic] = Field(min_length=1)
    steps: dict[str, NormalizedStep] = Field(min_length=1)
    course_assess: list[str] = Field(default_factory=list)
