from __future__ import annotations

import sys

from app.domain.chat.delivery.stream import stream_chat
from app.domain.chat.guidance.hints import build_hints
from app.domain.chat.session import models
from app.domain.chat.session.models import STREAM_PING_SECONDS, ChatContext, TutorView
from app.domain.chat.session.prepare import prepare_chat
from app.domain.llm import complete_chat_completion, stream_chat_completion

models.bind_package(sys.modules[__name__])

__all__ = [
    "ChatContext",
    "TutorView",
    "build_hints",
    "prepare_chat",
    "stream_chat",
    "complete_chat_completion",
    "stream_chat_completion",
    "STREAM_PING_SECONDS",
]
