from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.course_from_article.common.content.constants import _MAX_CHAPTERS
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_strategies import resolve_strategy_pack_id
from app.domain.ollama.model_select import (
    course_model_tier,
    model_is_course_capable,
)
from app.domain.ollama.runtime_policy import OllamaProfile


@dataclass(frozen=True, slots=True)
class LocalCoursePolicy:
    max_chapters: int
    outline_retries: int
    topic_retries: int
    stage_retries: int
    schema_temperature: float
    theory_max_tokens: int
    theory_section_max_tokens: int
    quiz_max_tokens: int
    practice_max_tokens: int
    theory_max_continues: int
    quality_rounds: int
    section_quality_rounds: int
    run_polish: bool
    sentences_per_window: int
    quiz_batch_size: int
    practice_batch_size: int
    warning: str | None = None
    web_glossary: bool = False
    strategy_pack: str = "author-full"
    split_long_theory: bool = True


_FULL_VOLUME = LocalCoursePolicy(
    max_chapters=_MAX_CHAPTERS,
    outline_retries=COURSE_LLM.outline_retries,
    topic_retries=COURSE_LLM.topic_retries,
    stage_retries=COURSE_LLM.stage_retries,
    schema_temperature=COURSE_LLM.json_temperature,
    theory_max_tokens=COURSE_LLM.theory_max_tokens,
    theory_section_max_tokens=COURSE_LLM.theory_section_max_tokens,
    quiz_max_tokens=COURSE_LLM.quiz_max_tokens,
    practice_max_tokens=COURSE_LLM.practice_max_tokens,
    theory_max_continues=COURSE_LLM.theory_max_continues,
    quality_rounds=COURSE_LLM.quality_rounds,
    section_quality_rounds=COURSE_LLM.quality_rounds,
    run_polish=True,
    sentences_per_window=3,
    quiz_batch_size=1,
    practice_batch_size=1,
    warning=None,
    strategy_pack="author-full",
    split_long_theory=True,
)


def model_meets_course_minimum(model: str) -> bool:
    return model_is_course_capable(model)


def local_course_policy_for(
    *,
    profile: OllamaProfile,
    model: str,
    web_glossary: bool = False,
) -> LocalCoursePolicy:
    pack_id = resolve_strategy_pack_id(meets_minimum=model_meets_course_minimum(model))
    if pack_id == "blocked":
        return LocalCoursePolicy(
            max_chapters=_FULL_VOLUME.max_chapters,
            outline_retries=0,
            topic_retries=0,
            stage_retries=0,
            schema_temperature=COURSE_LLM.json_temperature,
            theory_max_tokens=_FULL_VOLUME.theory_max_tokens,
            theory_section_max_tokens=_FULL_VOLUME.theory_section_max_tokens,
            quiz_max_tokens=_FULL_VOLUME.quiz_max_tokens,
            practice_max_tokens=_FULL_VOLUME.practice_max_tokens,
            theory_max_continues=_FULL_VOLUME.theory_max_continues,
            quality_rounds=0,
            section_quality_rounds=0,
            run_polish=False,
            sentences_per_window=3,
            quiz_batch_size=1,
            practice_batch_size=1,
            warning=(
                f"local course blocked-quality: model={model} is below qwen2.5:3b; "
                "pull qwen2.5:3b or qwen2.5:7b; strategy_pack=blocked"
            ),
            web_glossary=False,
            strategy_pack="blocked",
            split_long_theory=False,
        )

    strategy = course_model_tier(model)
    if strategy == "cpu":
        return replace(
            _FULL_VOLUME,
            sentences_per_window=1,
            theory_section_max_tokens=1200,
            theory_max_continues=1,
            outline_retries=COURSE_LLM.outline_retries + 2,
            topic_retries=COURSE_LLM.topic_retries + 2,
            stage_retries=COURSE_LLM.stage_retries + 2,
            quiz_batch_size=1,
            web_glossary=web_glossary,
            strategy_pack="author-full",
            split_long_theory=True,
            warning=(
                f"course strategy=cpu model={model}: full course volume, "
                "one-sentence theory windows, extra retries and quality passes"
            ),
        )
    return replace(
        _FULL_VOLUME,
        sentences_per_window=2 if profile.startswith("cpu") else 3,
        quiz_batch_size=1,
        web_glossary=web_glossary,
        strategy_pack="author-full",
        split_long_theory=True,
        warning=(f"course strategy=standard model={model}: full course volume and quality passes"),
    )
