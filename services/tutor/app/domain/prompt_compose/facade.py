from __future__ import annotations

from studio_contracts.packs.manifest import PhaseName

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
from .skills import course_skill_layers, provider_parts, role_path, skills_for

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
    "course_from_article_theory_prose_prompt",
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

_JSON_STAGE_SKILLS = frozenset({"course-stage-json", "pack-manifest-contract"})


def _skill_texts(names: list[str], *, skip: frozenset[str] = frozenset()) -> list[str]:
    return [load_prompt(f"skills/{name}") for name in names if name not in skip]


def _on_off(enabled: bool) -> str:
    return "ON" if enabled else "OFF"


def _author_parts_block() -> str:
    from app.domain.course_from_article.common.runtime.course_context import get_course_parts

    parts = get_course_parts()
    lines = [
        "## Author settings for THIS run (source of truth)",
        f"- Theory: {_on_off(parts.theory)}",
        f"- Quizzes: {_on_off(parts.quizzes)}",
        f"- Practice: {_on_off(parts.practice)}",
        "Emit only the parts that are ON. Do not invent a missing part "
        "because a skill mentions it.",
        "Turning a part OFF does not shrink the remaining parts. "
        "No filler. Cover the excerpt fully.",
    ]
    if not parts.quizzes:
        lines.append(
            "Quizzes OFF: no MCQs, self-checks, or «проверьте себя». "
            "Teach the decision inside the worked example."
        )
    if not parts.practice:
        lines.append(
            "Practice OFF: no homework, stubs, or «попробуй сам» as a task. "
            "Keep the worked example inside theory."
        )
    if not parts.theory:
        lines.append(
            "Theory OFF: do not write teaching chapters. "
            "Assess/practice (if ON) use the source excerpt."
        )
    return "\n".join(lines)


def _compose_course_prompt(request: PromptRequest, *, prose_output: bool = False) -> str:
    always, domain, stage = course_skill_layers(request)
    skip = _JSON_STAGE_SKILLS if prose_output else frozenset()
    parts: list[str] = []
    if prose_output:
        parts.append(load_prompt("shared/course_theory_prose_output"))
    parts.extend((load_prompt(role_path(request)), _author_parts_block()))
    if pack_id := (request.strategy_pack or "").strip():
        from app.domain.course_strategies import parse_strategy_pack, strategy_briefs

        parts.append(strategy_briefs(parse_strategy_pack(pack_id)))
    parts.extend(_skill_texts(always, skip=skip))
    parts.extend(load_prompt(path) for path in provider_parts(request))
    parts.extend(_skill_texts(domain))
    parts.extend(_skill_texts(stage))
    return render_prompt(
        compose_prompt(*parts),
        step_kind=request.step_kind,
        step_title=request.step_title,
    )


def build_system_prompt(request: PromptRequest) -> str:
    if request.mode == "course_from_article":
        return _compose_course_prompt(request)
    if request.mode in {"grade", "article_from_url"}:
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
    course_profile: str = "",
    local_runtime: bool = False,
    strategy_pack: str = "",
) -> str:
    return build_system_prompt(
        PromptRequest(
            mode="course_from_article",
            phase=None,
            step_kind=stage,
            step_title=stage,
            compact=compact,
            sql_aware=False,
            course_profile=course_profile,
            local_runtime=local_runtime,
            strategy_pack=strategy_pack,
        )
    )


def course_from_article_theory_prose_prompt(
    *,
    compact: bool = False,
    course_profile: str = "",
    local_runtime: bool = False,
    strategy_pack: str = "",
) -> str:
    return _compose_course_prompt(
        PromptRequest(
            mode="course_from_article",
            phase=None,
            step_kind="theory",
            step_title="theory",
            compact=compact,
            sql_aware=False,
            course_profile=course_profile,
            local_runtime=local_runtime,
            strategy_pack=strategy_pack,
        ),
        prose_output=True,
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
