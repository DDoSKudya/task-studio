from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnalyticsEventMessage(BaseModel):
    event_id: uuid.UUID
    event_type: str
    user_id: uuid.UUID
    session_id: uuid.UUID
    pack_version_id: uuid.UUID
    pack_title: str = ""
    topic_id: str = ""
    phase: str = ""
    step_id: str = ""
    payload: dict[str, object] = Field(default_factory=dict)
    event_time: datetime | None = None


class DailyProgressPoint(BaseModel):
    day: datetime
    sessions_started: int
    steps_completed: int


class ProgressResponse(BaseModel):
    points: list[DailyProgressPoint]
    total_sessions: int
    total_steps_completed: int


class StudySkipEntry(BaseModel):
    session_id: uuid.UUID
    pack_version_id: uuid.UUID
    pack_title: str
    topic_id: str
    skipped_at: datetime


class SkipsResponse(BaseModel):
    items: list[StudySkipEntry]
    total: int


class AttemptTimelineEntry(BaseModel):
    attempt_id: uuid.UUID
    session_id: uuid.UUID
    pack_title: str
    topic_id: str
    phase: str
    step_id: str
    passed: bool
    score: float
    created_at: datetime


class AttemptsTimelineResponse(BaseModel):
    items: list[AttemptTimelineEntry]
    next_cursor: str | None = None
