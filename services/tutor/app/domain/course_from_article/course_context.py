from __future__ import annotations

from contextvars import ContextVar

_course_profile: ContextVar[str] = ContextVar("course_profile", default="")


def set_course_profile(value: str) -> None:
    _course_profile.set(value)


def get_course_profile() -> str:
    return _course_profile.get()
