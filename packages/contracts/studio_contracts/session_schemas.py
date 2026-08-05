from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_contracts.manifest import PackPolicies, PhaseName
from studio_contracts.tutor_schemas import StepTutorInfo

SessionStatus = Literal["active", "completed", "abandoned"]


class StartSessionRequest(BaseModel):
    model_config = ConfigDict(strict=False)

    pack_version_id: uuid.UUID


class NavigateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    topic: str = Field(min_length=1)
    phase: PhaseName
    step: str = Field(min_length=1)

    complete_current: bool = False


class SubmitRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    submission: dict[str, object]


class AbandonSessionsRequest(BaseModel):
    model_config = ConfigDict(strict=False)

    pack_version_ids: list[uuid.UUID] = Field(default_factory=list)
    pack_titles: list[str] = Field(default_factory=list)


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


class PackProgressItem(BaseModel):
    id: uuid.UUID
    pack_version_id: uuid.UUID
    pack_title: str
    status: SessionStatus
    current_topic_id: str
    current_phase: PhaseName
    current_step_id: str
    started_at: datetime
    updated_at: datetime
    chapter_title: str
    progress_percent: int


class PhaseProgressInfo(BaseModel):
    topic_id: str
    study_completed: bool
    study_skipped: bool
    practice_completed: bool
    assess_completed: bool
    assess_best_score: float | None


class OutlineStep(BaseModel):
    topic_id: str
    phase: PhaseName
    step_id: str
    title: str
    kind: str
    index_label: str


class OutlineTopic(BaseModel):
    topic_id: str
    title: str
    index: int
    steps: list[OutlineStep] = Field(default_factory=list)


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
    outline: list[OutlineTopic] = Field(default_factory=list)
    passed_step_ids: list[str] = Field(default_factory=list)
    completed_step_ids: list[str] = Field(default_factory=list)
    started_at: datetime
    updated_at: datetime


class CourseDigestStep(BaseModel):
    step_id: str
    topic_id: str
    phase: PhaseName
    kind: str
    title: str
    index_label: str
    text: str
    has_video: bool = False


class CourseDigest(BaseModel):
    pack_version_id: uuid.UUID
    pack_title: str
    steps: list[CourseDigestStep] = Field(default_factory=list)


class StepNavTarget(BaseModel):
    topic: str
    phase: PhaseName
    step: str


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
    prev_step: StepNavTarget | None = None
    next_step: StepNavTarget | None = None


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
    status: Literal["completed", "pending"] = "completed"
    passed: bool = False
    score: float = 0.0
    feedback: str | None = None
    details: dict[str, object] = Field(default_factory=dict)
    phase_completed: bool = False


class AttemptCompleteRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    passed: bool
    score: float
    feedback: str | None = None
    details: dict[str, object] = Field(default_factory=dict)
