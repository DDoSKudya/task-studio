from __future__ import annotations

import json

from app.domain.course_from_article.common.content.textutil import _as_str
from app.domain.course_from_article.curriculum.outline.course_locale import locale_prompt_block
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


def _theory_critique_user_message(
    body: CourseFromArticleRequest,
    *,
    chapter: dict[str, str],
    content: str,
    outcomes: list[str],
) -> str:
    outcome_lines = "\n".join(f"- {item}" for item in outcomes[:8]) or "- (none)"
    excerpt = (_as_str(chapter.get("source_excerpt")) or "")[:4500]
    return "\n\n".join(
        [
            "## Stage\nquality",
            "## Mode\ncritique",
            "## Kind\ntheory",
            locale_prompt_block(body.locale),
            f"## Chapter title\n{chapter.get('title') or ''}",
            f"## Chapter purpose\n{chapter.get('purpose') or ''}",
            f"## Learning objective\n{chapter.get('learning_objective') or ''}",
            f"## Outcomes\n{outcome_lines}",
            f"## Source excerpt (ground truth)\n{excerpt}",
            f"## Theory draft\n{content[:7000]}",
            "## Output\nJSON {ok, score, issues[], must_fix[]}.",
        ]
    )


def _theory_patch_user_message(
    body: CourseFromArticleRequest,
    *,
    chapter: dict[str, str],
    content: str,
    must_fix: list[str],
) -> str:
    default_fix = "- Strengthen grounding on the excerpt"
    fixes = "\n".join(f"- {item}" for item in must_fix[:5]) or default_fix
    excerpt = (_as_str(chapter.get("source_excerpt")) or "")[:4500]
    objective = chapter.get("learning_objective") or chapter.get("purpose") or ""
    return "\n\n".join(
        [
            "## Stage\nquality",
            "## Mode\nrewrite",
            "## Kind\ntheory",
            locale_prompt_block(body.locale),
            f"## Chapter title\n{chapter.get('title') or ''}",
            f"## Learning objective\n{objective}",
            f"## Must fix\n{fixes}",
            f"## Source excerpt (ground truth)\n{excerpt}",
            f"## Draft to revise\n{content[:7000]}",
            "## Output\nRevised chapter markdown only.",
        ]
    )


def _dump_step(payload: dict[str, object], *, limit: int) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)[:limit]


def _quiz_critique_user_message(
    body: CourseFromArticleRequest,
    *,
    quiz: dict[str, object],
    outcomes: list[str],
    context: str,
) -> str:
    outcome_lines = "\n".join(f"- {item}" for item in outcomes[:8]) or "- (none)"
    slim = {
        key: quiz.get(key)
        for key in ("id", "title", "question", "choices", "answer")
        if key in quiz
    }
    return "\n\n".join(
        [
            "## Stage\nquality",
            "## Mode\ncritique",
            "## Kind\nquiz",
            locale_prompt_block(body.locale),
            f"## Outcomes\n{outcome_lines}",
            f"## Grounding context\n{context[:4500]}",
            f"## Quiz draft\n{_dump_step(slim, limit=3500)}",
            "## Output\nJSON {ok, score, issues[], must_fix[]}.",
        ]
    )


def _quiz_patch_user_message(
    body: CourseFromArticleRequest,
    *,
    quiz: dict[str, object],
    must_fix: list[str],
    context: str,
) -> str:
    fixes = "\n".join(f"- {item}" for item in must_fix[:5]) or "- Improve the MCQ"
    slim = {
        key: quiz.get(key)
        for key in ("id", "title", "question", "choices", "answer")
        if key in quiz
    }
    return "\n\n".join(
        [
            "## Stage\nquality",
            "## Mode\nrewrite",
            "## Kind\nquiz",
            locale_prompt_block(body.locale),
            f"## Must fix\n{fixes}",
            f"## Grounding context\n{context[:4500]}",
            f"## Quiz draft\n{_dump_step(slim, limit=3500)}",
            "## Output\nJSON one quiz {id,title,question,choices[4],answer}.",
        ]
    )


def _practice_critique_user_message(
    body: CourseFromArticleRequest,
    *,
    task: dict[str, object],
    outcomes: list[str],
    context: str,
    kind: str,
) -> str:
    outcome_lines = "\n".join(f"- {item}" for item in outcomes[:8]) or "- (none)"
    keys = (
        "id",
        "kind",
        "level",
        "title",
        "content",
        "template",
        "tests",
        "checker",
        "rubric",
        "runtime",
    )
    slim = {key: task.get(key) for key in keys if key in task}
    return "\n\n".join(
        [
            "## Stage\nquality",
            "## Mode\ncritique",
            f"## Kind\n{kind}",
            locale_prompt_block(body.locale),
            f"## Outcomes\n{outcome_lines}",
            f"## Grounding context\n{context[:4500]}",
            f"## Practice draft\n{_dump_step(slim, limit=4500)}",
            "## Output\nJSON {ok, score, issues[], must_fix[]}.",
        ]
    )


def _practice_patch_user_message(
    body: CourseFromArticleRequest,
    *,
    task: dict[str, object],
    must_fix: list[str],
    context: str,
    kind: str,
) -> str:
    fixes = "\n".join(f"- {item}" for item in must_fix[:5]) or "- Improve the practice task"
    keys = (
        "id",
        "kind",
        "level",
        "title",
        "content",
        "template",
        "tests",
        "checker",
        "rubric",
        "runtime",
    )
    slim = {key: task.get(key) for key in keys if key in task}
    return "\n\n".join(
        [
            "## Stage\nquality",
            "## Mode\nrewrite",
            f"## Kind\n{kind}",
            locale_prompt_block(body.locale),
            f"## Must fix\n{fixes}",
            f"## Grounding context\n{context[:4500]}",
            f"## Practice draft\n{_dump_step(slim, limit=4500)}",
            "## Output\nJSON one practice task object.",
        ]
    )
