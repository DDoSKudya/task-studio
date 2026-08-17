from __future__ import annotations

from app.domain.course_from_article.curriculum.outline.messages_outline import (
    _analyze_chapter_user_message,
    _analyze_user_message,
    _theory_content_user_message,
    _theory_meta_user_message,
    _theory_section_user_message,
)
from app.domain.course_from_article.practice.messages_practice import (
    _code_one_task_user_message,
    _polish_one_user_message,
    _quiz_one_user_message,
    _task_one_user_message,
)
from app.domain.course_from_article.quality.messages_quality import (
    _practice_critique_user_message,
    _practice_patch_user_message,
    _quiz_critique_user_message,
    _quiz_patch_user_message,
    _theory_critique_user_message,
    _theory_patch_user_message,
)

__all__ = [
    "_analyze_chapter_user_message",
    "_analyze_user_message",
    "_code_one_task_user_message",
    "_polish_one_user_message",
    "_practice_critique_user_message",
    "_practice_patch_user_message",
    "_quiz_critique_user_message",
    "_quiz_one_user_message",
    "_quiz_patch_user_message",
    "_task_one_user_message",
    "_theory_content_user_message",
    "_theory_critique_user_message",
    "_theory_meta_user_message",
    "_theory_patch_user_message",
    "_theory_section_user_message",
]
