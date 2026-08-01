from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from studio_contracts.manifest import PhaseName
from studio_contracts.session_schemas import StepContent

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"

PromptMode = Literal[
    "chat", "hints", "pack_studio", "grade", "course_from_article", "article_from_url"
]

_SQL_HINT_RE = re.compile(
    r"\b(select|insert|update|delete|join|from|where|group\s+by|sql)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ContextBudget:
    outline_steps: int
    page_chars: int
    starter_chars: int
    history_messages: int


BUDGET_COMPACT = ContextBudget(
    outline_steps=24,
    page_chars=1200,
    starter_chars=400,
    history_messages=6,
)
BUDGET_FULL = ContextBudget(
    outline_steps=80,
    page_chars=3500,
    starter_chars=900,
    history_messages=24,
)


@dataclass(frozen=True, slots=True)
class PromptRequest:
    mode: PromptMode
    phase: PhaseName | None
    step_kind: str
    step_title: str
    compact: bool = False
    sql_aware: bool = False


def load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def render_prompt(template: str, **values: object) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def compose_prompt(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def context_budget(*, compact: bool) -> ContextBudget:
    return BUDGET_COMPACT if compact else BUDGET_FULL


def step_looks_like_sql(step: StepContent) -> bool:
    if step.editor:
        runtime = str(step.editor.get("runtime") or "").lower()
        language = str(step.editor.get("language") or "").lower()
        if "sql" in runtime or "sql" in language:
            return True
    blob = json.dumps(step.content, ensure_ascii=False)
    if step.editor:
        blob += json.dumps(step.editor, ensure_ascii=False)
    return bool(_SQL_HINT_RE.search(blob))
