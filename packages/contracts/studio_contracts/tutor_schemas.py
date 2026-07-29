from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_contracts.manifest import PhaseName

TutorMode = Literal["hint", "chat"]
HintSource = Literal["fallback", "llm"]
TutorProviderMode = Literal["ollama", "external", "cursor"]


class TutorProviderProfile(BaseModel):
    model_config = ConfigDict(strict=True)

    provider_url: str | None = None
    api_key_encrypted: str | None = None
    model: str | None = None


class TutorSettings(BaseModel):
    model_config = ConfigDict(strict=True)

    enabled: bool = True
    provider_url: str | None = None
    api_key_encrypted: str | None = None
    daily_limit: int = Field(default=0, ge=0)
    model: str | None = None
    active_provider: TutorProviderMode | None = None
    provider_profiles: dict[str, TutorProviderProfile] = Field(default_factory=dict)


class TutorChatTurn(BaseModel):
    model_config = ConfigDict(strict=False)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class TutorChatRequest(BaseModel):
                                                                                            
    model_config = ConfigDict(strict=False)

    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)
    history: list[TutorChatTurn] = Field(default_factory=list, max_length=24)


class TutorWarmupRequest(BaseModel):
    model_config = ConfigDict(strict=False)

    session_id: uuid.UUID


class TutorWarmupResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    ok: bool
    skipped: bool = False
    reused: bool = False
    detail: str = ""


class TutorHintResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    hints: list[str]
    source: HintSource


class TutorLlmStatus(BaseModel):
    model_config = ConfigDict(strict=True)

    ok: bool
    provider: Literal["ollama", "external"]
    detail: str
    models: list[str] = Field(default_factory=list)
    default_model: str | None = None


class TutorLlmTestRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    provider: Literal["ollama", "external"] = "ollama"
    provider_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class TutorGradeRequest(BaseModel):
                                                                                            

    model_config = ConfigDict(strict=False)

    kind: Literal["quiz", "code", "task", "lab"]
    step: dict[str, object]
    submission: dict[str, object]


class TutorGradeResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    feedback: str
    rationale: str = ""
    model: str | None = None
    usable: bool = True


class StepTutorInfo(BaseModel):
    model_config = ConfigDict(strict=True)

    enabled: bool
    mode: TutorMode


def infer_tutor_provider(provider_url: str | None) -> TutorProviderMode:
    cleaned = (provider_url or "").strip().casefold()
    if not cleaned:
        return "ollama"
    if "cursor-proxy" in cleaned:
        return "cursor"
    return "external"


def _normalize_tutor_blob(raw: dict[str, object]) -> dict[str, object]:
    blob = dict(raw)
    profiles_raw = blob.get("provider_profiles")
    profiles: dict[str, object] = (
        dict(profiles_raw) if isinstance(profiles_raw, dict) else {}
    )
    active = blob.get("active_provider")
    provider_url_raw = blob.get("provider_url")
    provider_url = provider_url_raw if isinstance(provider_url_raw, str) else None
    if not isinstance(active, str) or active not in {"ollama", "external", "cursor"}:
        active = infer_tutor_provider(provider_url)
    blob["active_provider"] = active

    if not profiles:
        profiles[active] = {
            "provider_url": blob.get("provider_url"),
            "api_key_encrypted": blob.get("api_key_encrypted"),
            "model": blob.get("model"),
        }

    for mode in ("ollama", "external", "cursor"):
        entry = profiles.get(mode)
        if not isinstance(entry, dict):
            profiles[mode] = {}
            continue
        profiles[mode] = {
            key: entry.get(key)
            for key in ("provider_url", "api_key_encrypted", "model")
            if key in entry
        }

    blob["provider_profiles"] = profiles
    active_profile = profiles.get(active)
    if isinstance(active_profile, dict):
        for key in ("provider_url", "api_key_encrypted", "model"):
            if key in active_profile:
                blob[key] = active_profile.get(key)
    return blob


def parse_tutor_settings(user_settings: dict[str, object]) -> TutorSettings:
    raw = user_settings.get("tutor")
    if isinstance(raw, dict):
        settings = TutorSettings.model_validate(_normalize_tutor_blob(raw))
                                                                             
        if not settings.enabled:
            return settings.model_copy(update={"enabled": True})
        return settings
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
                                                                           
    _ = user_enabled
    return True


def tutor_mode_for_phase(phase: PhaseName) -> TutorMode | None:
    if phase == "study":
        return "hint"
    if phase == "practice":
        return "chat"
    return None
