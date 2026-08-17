from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CourseLlmLimits:
    quiz_max_tokens: int
    practice_max_tokens: int
    practice_stage_max_tokens: int
    code_stage_max_tokens: int
    theory_max_tokens: int
    theory_section_max_tokens: int
    theory_max_continues: int
    theory_temperature: float
    theory_patch_temperature: float
    theory_patch_continues: int
    json_temperature: float
    json_temperature_cloud: float
    json_temperature_compact: float
    json_continues_compact: int
    max_quiz_attempts: int
    quality_rounds: int
    outline_retries: int
    topic_retries: int
    stage_retries: int
    order_max_tokens: int
    outline_label_max_tokens: int
    polish_max_tokens: int


COURSE_LLM = CourseLlmLimits(
    quiz_max_tokens=2000,
    practice_max_tokens=2200,
    practice_stage_max_tokens=4200,
    code_stage_max_tokens=5200,
    theory_max_tokens=4500,
    theory_section_max_tokens=2200,
    theory_max_continues=6,
    theory_temperature=0.15,
    theory_patch_temperature=0.12,
    theory_patch_continues=1,
    json_temperature=0.0,
    json_temperature_cloud=0.15,
    json_temperature_compact=0.2,
    json_continues_compact=2,
    max_quiz_attempts=5,
    quality_rounds=2,
    outline_retries=3,
    topic_retries=4,
    stage_retries=2,
    order_max_tokens=700,
    outline_label_max_tokens=2400,
    polish_max_tokens=2400,
)


def json_stage_temperature(*, local_runtime: bool, compact: bool = False) -> float:
    if local_runtime:
        return COURSE_LLM.json_temperature
    if compact:
        return COURSE_LLM.json_temperature_compact
    return COURSE_LLM.json_temperature_cloud


def json_stage_top_p(*, local_runtime: bool, compact: bool = False) -> float | None:
    if local_runtime or not compact:
        return None
    return 0.9


def json_stage_continues(*, compact: bool) -> int:
    if compact:
        return COURSE_LLM.json_continues_compact
    return COURSE_LLM.theory_max_continues
