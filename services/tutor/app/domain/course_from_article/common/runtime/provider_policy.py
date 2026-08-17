from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config import TutorConfig
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_strategies.policy import resolve_strategy_pack_id
from app.domain.llm.target import LlmTarget, is_cursor_target, is_ollama_target
from app.domain.ollama.model_select import course_model_tier, model_is_course_capable

CourseProviderKind = Literal["ollama", "external", "cursor"]


@dataclass(frozen=True, slots=True)
class CourseHarnessPolicy:
    provider: CourseProviderKind
    compact: bool
    run_polish: bool
    quiz_fail_soft: bool
    code_fail_soft: bool
    max_quiz_attempts: int
    quiz_max_tokens: int
    split_long_theory: bool
    theory_max_continues: int
    sectional_theory: bool
    theory_quality_rounds: int
    quiz_quality_rounds: int
    practice_quality_rounds: int
    strategy_pack: str = "author-full"
    theory_sentences_per_window: int = 3


def detect_course_provider(config: TutorConfig, target: LlmTarget) -> CourseProviderKind:
    if is_ollama_target(config, target):
        return "ollama"
    if is_cursor_target(target):
        return "cursor"
    return "external"


def course_harness_policy(
    config: TutorConfig,
    target: LlmTarget,
    *,
    ollama_profile: str,
) -> CourseHarnessPolicy:
    _ = ollama_profile
    limits = COURSE_LLM
    provider = detect_course_provider(config, target)
    model = (target.model or "").strip()

    if provider != "ollama":
        pack_id = "author-full"
        strategy = "standard"
    else:
        pack_id = resolve_strategy_pack_id(meets_minimum=model_is_course_capable(model))
        strategy = course_model_tier(model)
    enabled = pack_id == "author-full"
    sectional = provider == "ollama" and enabled
    sentences_per_window = 1 if strategy == "cpu" else 3
    quality_rounds = limits.quality_rounds if enabled else 0
    return CourseHarnessPolicy(
        provider=provider,
        compact=False,
        run_polish=enabled,
        quiz_fail_soft=False,
        code_fail_soft=False,
        max_quiz_attempts=limits.max_quiz_attempts,
        quiz_max_tokens=limits.quiz_max_tokens,
        split_long_theory=enabled,
        theory_max_continues=1 if sectional else limits.theory_max_continues,
        theory_sentences_per_window=sentences_per_window,
        sectional_theory=sectional,
        theory_quality_rounds=quality_rounds,
        quiz_quality_rounds=quality_rounds,
        practice_quality_rounds=quality_rounds,
        strategy_pack=pack_id,
    )
