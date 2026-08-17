from __future__ import annotations

from app.domain.context import fetch_user_settings
from app.domain.course_from_article.common.content.constants import _MAX_ARTICLE_FOR_PROMPT
from app.domain.course_from_article.common.content.messages import _theory_content_user_message
from app.domain.course_from_article.common.content.normalize import (
    _normalize_book_spine,
    _normalize_chapters,
    _normalize_deviations,
    _normalize_theory_step,
)
from app.domain.course_from_article.common.content.textutil import (
    _articles_from_body,
    _combined_corpus,
    _video_steps_from_sources,
)
from app.domain.course_from_article.curriculum.theory.theory import (
    _theory_parallel_limit,
    _theory_serial_count,
)
from app.domain.course_from_article.pack.assemble import (
    _assemble_manifest,
    _repair_code_fences,
    _retarget_code_fences,
)
from app.domain.course_from_article.quality.polish import (
    _apply_book_polish_edits,
    _chapter_opening,
)
from app.domain.course_from_article.workflow.events.progress import (
    _parse_json_object,
    _sse_event,
    _stage_json,
)
from app.domain.course_from_article.workflow.pipeline.pipeline import (
    generate_course_from_article,
    iter_course_from_article,
    stream_course_from_article,
)
from app.domain.llm import is_ollama_target, resolve_llm_target

__all__ = [
    "generate_course_from_article",
    "stream_course_from_article",
    "iter_course_from_article",
    "fetch_user_settings",
    "is_ollama_target",
    "resolve_llm_target",
    "_assemble_manifest",
    "_repair_code_fences",
    "_retarget_code_fences",
    "_MAX_ARTICLE_FOR_PROMPT",
    "_theory_content_user_message",
    "_normalize_book_spine",
    "_normalize_chapters",
    "_normalize_deviations",
    "_normalize_theory_step",
    "_apply_book_polish_edits",
    "_chapter_opening",
    "_parse_json_object",
    "_sse_event",
    "_stage_json",
    "_articles_from_body",
    "_combined_corpus",
    "_video_steps_from_sources",
    "_theory_parallel_limit",
    "_theory_serial_count",
]
