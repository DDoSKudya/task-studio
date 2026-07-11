from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GradingSettings:
    piston_url: str
    piston_timeout_seconds: float


def load_settings() -> GradingSettings:
    return GradingSettings(
        piston_url=os.getenv("PISTON_URL", "http://piston:2000").rstrip("/"),
        piston_timeout_seconds=float(os.getenv("PISTON_TIMEOUT_SECONDS", "10")),
    )
