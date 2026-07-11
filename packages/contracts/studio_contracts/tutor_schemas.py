from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_contracts.manifest import PhaseName

TutorMode = Literal["hint", "chat"]
HintSource = Literal["fallback", "llm"]


class TutorSettings(BaseModel):
    model_config = ConfigDict(strict=True)

    enabled: bool = True
    provider_url: str | None = None
    api_key_encrypted: str | None = None
    daily_limit: int = Field(default=0, ge=0)
    model: str | None = None


class TutorChatRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)


class TutorHintResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    hints: list[str]
    source: HintSource


class StepTutorInfo(BaseModel):
    model_config = ConfigDict(strict=True)

    enabled: bool
    mode: TutorMode


def parse_tutor_settings(user_settings: dict[str, object]) -> TutorSettings:
    raw = user_settings.get("tutor")
    if isinstance(raw, dict):
        return TutorSettings.model_validate(raw)
    return TutorSettings()


def tutor_allowed(
    phase: PhaseName,
    *,
    pack_tutor_enabled: bool,
    user_enabled: bool,
) -> bool:
    if phase == "assess":
        return False
    if not pack_tutor_enabled:
        return False
    return user_enabled


def tutor_mode_for_phase(phase: PhaseName) -> TutorMode | None:
    if phase == "study":
        return "hint"
    if phase == "practice":
        return "chat"
    return None
