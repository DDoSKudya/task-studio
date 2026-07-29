from __future__ import annotations

import sys

from app.domain.llm import complete_chat_completion, stream_chat_completion

from . import models as _models
from .hints import build_hints
from .models import _STREAM_PING_SECONDS, ChatContext, TutorView
from .prepare import prepare_chat
from .stream import stream_chat

_models.bind_package(sys.modules[__name__])

__all__ = [
    "ChatContext",
    "TutorView",
    "build_hints",
    "prepare_chat",
    "stream_chat",
    "complete_chat_completion",
    "stream_chat_completion",
    "_STREAM_PING_SECONDS",
]
