from __future__ import annotations

import re


def external_step_id_from_step(step: dict[str, object]) -> str | None:
    raw = step.get("external_step_id")
    if isinstance(raw, str) and raw.strip().isdigit():
        return raw.strip()
    step_id = step.get("id")
    if isinstance(step_id, str) and (match := re.fullmatch(r"step-(\d+)", step_id)):
        return match[1]
    return None


def is_stepik_quiz(step: dict[str, object]) -> bool:
    platform = step.get("source_platform")
    return isinstance(platform, str) and platform.casefold() == "stepik"
