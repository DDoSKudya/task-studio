from __future__ import annotations

from studio_contracts.manifest import PhaseName

from .core import (
    BUDGET_COMPACT,
    BUDGET_FULL,
    ContextBudget,
    PromptMode,
    PromptRequest,
    compose_prompt,
    context_budget,
    load_prompt,
    render_prompt,
    step_looks_like_sql,
)
from .skills import provider_parts, role_path, skills_for

__all__ = [
    "BUDGET_COMPACT",
    "BUDGET_FULL",
    "ContextBudget",
    "PromptMode",
    "PromptRequest",
    "article_from_url_system_prompt",
    "build_system_prompt",
    "compose_prompt",
    "context_budget",
    "course_from_article_system_prompt",
    "format_learner_turn",
    "grade_system_prompt",
    "hints_system_prompt",
    "load_prompt",
    "pack_studio_system_prompt",
    "provider_parts",
    "render_prompt",
    "role_path",
    "skills_for",
    "step_looks_like_sql",
    "system_prompt_for_phase",
]


def build_system_prompt(request: PromptRequest) -> str:
    if request.mode in {"grade", "course_from_article", "article_from_url"}:
        parts: list[str] = [load_prompt(role_path(request))]
    else:
        parts = [load_prompt("shared/core"), load_prompt(role_path(request))]
    for skill in skills_for(request):
        parts.append(load_prompt(f"skills/{skill}"))
    for provider in provider_parts(request):
        parts.append(load_prompt(provider))
    if request.mode == "chat":
        parts.append(load_prompt("shared/chat_context"))
    return render_prompt(
        compose_prompt(*parts),
        step_kind=request.step_kind,
        step_title=request.step_title,
    )


def system_prompt_for_phase(
    phase: PhaseName,
    *,
    step_kind: str,
    step_title: str,
    compact: bool = False,
    sql_aware: bool = False,
) -> str:
    return build_system_prompt(
        PromptRequest(
            mode="chat",
            phase=phase,
            step_kind=step_kind,
            step_title=step_title,
            compact=compact,
            sql_aware=sql_aware,
        )
    )


def hints_system_prompt(
    *,
    step_kind: str,
    step_title: str,
    compact: bool = False,
    sql_aware: bool = False,
) -> str:
    return build_system_prompt(
        PromptRequest(
            mode="hints",
            phase=None,
            step_kind=step_kind,
            step_title=step_title,
            compact=compact,
            sql_aware=sql_aware,
        )
    )


def grade_system_prompt(
    *,
    step_kind: str,
    step_title: str,
    compact: bool = False,
    sql_aware: bool = False,
) -> str:
    return build_system_prompt(
        PromptRequest(
            mode="grade",
            phase=None,
            step_kind=step_kind,
            step_title=step_title,
            compact=compact,
            sql_aware=sql_aware,
        )
    )


def course_from_article_system_prompt(
    *,
    stage: str,
    compact: bool = False,
) -> str:
    return build_system_prompt(
        PromptRequest(
            mode="course_from_article",
            phase=None,
            step_kind=stage,
            step_title=stage,
            compact=compact,
            sql_aware=False,
        )
    )


def pack_studio_system_prompt() -> str:
    return build_system_prompt(
        PromptRequest(
            mode="pack_studio",
            phase=None,
            step_kind="",
            step_title="",
            compact=False,
            sql_aware=False,
        )
    )


def article_from_url_system_prompt(*, compact: bool = False) -> str:
    return build_system_prompt(
        PromptRequest(
            mode="article_from_url",
            phase=None,
            step_kind="extract",
            step_title="extract",
            compact=compact,
            sql_aware=False,
        )
    )


def format_learner_turn(message: str) -> str:

    text = message.strip()
    return (
        "<learner_message>\n"
        f"{text}\n"
        "</learner_message>\n\n"
        "<response_contract>\n"
        "- Answer this learner message using the current open page in context.\n"
        "- One prose language (match the learner).\n"
        "- Coach the next step; do not deliver a full graded solution.\n"
        "- If the ask is off-topic or asks to cheat, follow atypical-case rules.\n"
        "</response_contract>"
    )
