from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_contracts.manifest import PackPolicies, PhaseName
from studio_contracts.tutor_schemas import StepTutorInfo

SessionStatus = Literal["active", "completed", "abandoned"]


class StartSessionRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    pack_version_id: uuid.UUID


class NavigateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    topic: str = Field(min_length=1)
    phase: PhaseName
    step: str = Field(min_length=1)


class SubmitRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    submission: dict[str, object]


class SessionSummary(BaseModel):
    id: uuid.UUID
    pack_version_id: uuid.UUID
    pack_title: str
    status: SessionStatus
    current_topic_id: str
    current_phase: PhaseName
    current_step_id: str
    started_at: datetime
    updated_at: datetime


class PhaseProgressInfo(BaseModel):
    topic_id: str
    study_completed: bool
    study_skipped: bool
    practice_completed: bool
    assess_completed: bool
    assess_best_score: float | None


class SessionState(BaseModel):
    id: uuid.UUID
    pack_version_id: uuid.UUID
    pack_title: str
    status: SessionStatus
    current_topic_id: str
    current_phase: PhaseName
    current_step_id: str
    policies: PackPolicies
    phase_progress: list[PhaseProgressInfo]
    started_at: datetime
    updated_at: datetime


class StepContent(BaseModel):
    topic_id: str
    phase: PhaseName
    step_id: str
    kind: str
    title: str
    content: dict[str, object]
    editor: dict[str, object] | None = None
    tutor: StepTutorInfo | None = None
    transitions: dict[str, str] = Field(default_factory=dict)


class AttemptInfo(BaseModel):
    id: uuid.UUID
    topic_id: str
    phase: PhaseName
    step_id: str
    attempt_number: int
    submission: dict[str, object]
    result: dict[str, object] | None
    created_at: datetime


class SubmitResult(BaseModel):
    attempt_id: uuid.UUID
    passed: bool
    score: float
    feedback: str | None
    phase_completed: bool
