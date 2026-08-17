from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

from app.domain.llm import LlmTarget
from studio_contracts.api.session_schemas import CourseDigest, SessionState, StepContent
from studio_contracts.api.tutor_schemas import TutorSettings


@dataclass(frozen=True, slots=True)
class TutorView:
    session: SessionState
    step: StepContent
    user_settings: TutorSettings
    digest: CourseDigest


@dataclass(frozen=True, slots=True)
class ChatContext:
    target: LlmTarget
    system_prompt: str
    conversation_id: str
    compact: bool = False


STREAM_PING_SECONDS = 12.0
OLLAMA_DRAFT_TEMPERATURE = 0.35
OLLAMA_DRAFT_TOP_P = 0.9
OLLAMA_POLISH_TEMPERATURE = 0.2
OLLAMA_POLISH_TOP_P = 0.85

OLLAMA_DRAFT_MAX_TOKENS = 512
OLLAMA_POLISH_MAX_TOKENS = 512

_PACKAGE: ModuleType | None = None


def bind_package(package: ModuleType) -> None:
    global _PACKAGE
    _PACKAGE = package


def _pkg() -> ModuleType:
    if _PACKAGE is None:
        msg = "chat package not bound"
        raise RuntimeError(msg)
    return _PACKAGE


async def complete_bound_chat(*args, **kwargs):
    return await _pkg().complete_chat_completion(*args, **kwargs)


async def iter_bound_stream_tokens(*args, **kwargs):
    async for token in _pkg().stream_chat_completion(*args, **kwargs):
        yield token


def stream_ping_seconds() -> float:
    return float(_pkg().STREAM_PING_SECONDS)
