from __future__ import annotations

from contextvars import ContextVar
from typing import NamedTuple

_course_profile: ContextVar[str] = ContextVar("course_profile", default="")
_strategy_pack: ContextVar[str] = ContextVar("strategy_pack", default="")


class CourseParts(NamedTuple):
    theory: bool = True
    quizzes: bool = True
    practice: bool = True


_DEFAULT_COURSE_PARTS = CourseParts()
_course_parts: ContextVar[CourseParts] = ContextVar(
    "course_parts",
    default=_DEFAULT_COURSE_PARTS,
)


def set_course_profile(value: str) -> None:
    _course_profile.set(value)


def get_course_profile() -> str:
    return _course_profile.get()


def set_strategy_pack(value: str) -> None:
    _strategy_pack.set((value or "").strip())


def get_strategy_pack() -> str:
    return _strategy_pack.get()


def set_course_parts(*, theory: bool, quizzes: bool, practice: bool) -> None:
    _course_parts.set(CourseParts(theory=theory, quizzes=quizzes, practice=practice))


def get_course_parts() -> CourseParts:
    return _course_parts.get()
