from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PistonJob:
    language: str
    version: str
    files: list[dict[str, str]]
    args: list[str] | None = None
