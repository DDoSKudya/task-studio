from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from studio_contracts.studio_schemas import CourseFromArticleRequest

from .code_suitability import (
    code_suitability_score,
    code_tasks_recommended,
    should_prompt_code_gate,
)
from .course_profile import CourseProfile
from .progress import _stage_event


@dataclass
class CodeSuitabilityResult:
    score: float = 0.0
    recommended: bool = True
    halted: bool = False
    action: str | None = None


async def iter_code_suitability_stage(
    *,
    body: CourseFromArticleRequest,
    profile: CourseProfile,
    band: tuple[float, float],
    result: CodeSuitabilityResult,
) -> AsyncIterator[dict[str, object]]:
    score = code_suitability_score(profile=profile, runtime=body.runtime)
    recommended = code_tasks_recommended(score=score, include_code=bool(body.include_code))
    result.score = score
    result.recommended = recommended

    yield _stage_event(
        stage="code_suitability",
        status="done",
        progress=band[1],
        message="Code task suitability evaluated",
        message_key="codeSuitabilityDone",
        detail={
            "score": score,
            "recommended": recommended,
            "profile": profile,
        },
    )

    policy = body.code_suitability_policy
    if body.code_suitability_action:
        result.action = body.code_suitability_action
        return

    if should_prompt_code_gate(score=score, include_code=bool(body.include_code), policy=policy):
        result.halted = True
        yield {
            "type": "code_suitability_gate",
            "stage": "code_suitability",
            "status": "needs_confirmation",
            "progress": band[1],
            "message": "Code tasks may not fit this course — choose how to continue",
            "message_key": "codeSuitabilityGate",
            "detail": {
                "score": score,
                "profile": profile,
                "options": ["keep_code", "open_tasks", "no_practice"],
            },
        }
        return

    if policy == "auto_open" and body.include_code and not recommended:
        result.action = "open_tasks"
    elif policy == "auto_skip" and body.include_code and not recommended:
        result.action = "no_practice"
