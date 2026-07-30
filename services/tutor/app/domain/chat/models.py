from __future__ import annotations

from dataclasses import dataclass

from app.domain.llm import LlmTarget
from studio_contracts.session_schemas import CourseDigest, SessionState, StepContent
from studio_contracts.tutor_schemas import TutorSettings


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


_STREAM_PING_SECONDS = 12.0
_OLLAMA_DRAFT_TEMPERATURE = 0.35
_OLLAMA_DRAFT_TOP_P = 0.9
_OLLAMA_POLISH_TEMPERATURE = 0.2
_OLLAMA_POLISH_TOP_P = 0.85

_OLLAMA_DRAFT_MAX_TOKENS = 512
_OLLAMA_POLISH_MAX_TOKENS = 512


_PACKAGE = None


def bind_package(package: object) -> None:
    global _PACKAGE
    _PACKAGE = package


def _pkg() -> object:
    if _PACKAGE is None:
        msg = "chat package not bound"
        raise RuntimeError(msg)
    return _PACKAGE


async def _complete_chat_completion(*args, **kwargs):
    return await _pkg().complete_chat_completion(*args, **kwargs)


async def _iter_stream_tokens(*args, **kwargs):
    async for token in _pkg().stream_chat_completion(*args, **kwargs):
        yield token


def _stream_ping_seconds() -> float:
    return float(_pkg()._STREAM_PING_SECONDS)
