from __future__ import annotations

from dataclasses import dataclass

from app.domain.harness.shared import PistonJob


@dataclass(frozen=True, slots=True)
class HarnessJob:
    job: PistonJob
    checker: str


@dataclass(frozen=True, slots=True)
class HarnessBlocked:
    checker: str
    reason: str
    ungradable: str
