from __future__ import annotations

from typing import Literal

AdapterRole = Literal[
    "course-map",
    "course-theory",
    "course-quiz",
    "course-practice",
    "tutor-chat",
]

ADAPTER_ROLES: tuple[AdapterRole, ...] = (
    "course-map",
    "course-theory",
    "course-quiz",
    "course-practice",
    "tutor-chat",
)

_MODEL_PREFIX = "task-studio-"

MIN_GOLD_PAIRS: dict[AdapterRole, int] = {
    "course-map": 20,
    "course-theory": 40,
    "course-quiz": 40,
    "course-practice": 20,
    "tutor-chat": 40,
}


class AdapterRefused(ValueError):
    pass


def ollama_model_for_role(role: AdapterRole) -> str:
    return f"{_MODEL_PREFIX}{role}:latest"


def is_adapter_model(model: str) -> bool:
    name = model.casefold()
    return name.startswith(_MODEL_PREFIX) and any(
        f"{_MODEL_PREFIX}{role}" in name for role in ADAPTER_ROLES
    )


def parse_role(raw: str) -> AdapterRole | None:
    text = raw.strip()
    for role in ADAPTER_ROLES:
        if text == role:
            return role
    return None
