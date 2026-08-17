from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
from app.domain.course_from_article.common.content.textutil import _as_str
from app.domain.course_from_article.common.runtime.course_context import (
    get_course_profile,
    get_strategy_pack,
)
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_from_article.common.runtime.stage_llm import _stage_json
from app.domain.course_from_article.curriculum.outline.normalize_outline import _title_fingerprint
from app.domain.course_from_article.quality.messages_quality import (
    _theory_critique_user_message,
    _theory_patch_user_message,
)
from app.domain.errors import TutorError
from app.domain.llm import LlmTarget, complete_text_until_done
from app.domain.llm.content.prose_dedupe import clean_theory_markdown, collapse_repeated_prose
from app.domain.llm.transport.request import looks_like_ollama_endpoint
from app.domain.prompt_compose import compose_prompt, course_from_article_theory_prose_prompt
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

_MIN_CHARS = 420
_GROUND_MIN_OVERLAP = 0.04
_THROAT_RE = re.compile(
    r"(в этой главе|in this chapter|we will (learn|cover)|сегодня мы|давайте разбер)",
    re.IGNORECASE,
)


def theory_content_is_usable(content: object) -> bool:
    return len(str(content or "").strip()) >= _MIN_CHARS


@dataclass(frozen=True, slots=True)
class TheoryCritique:
    ok: bool
    score: float
    issues: list[str] = field(default_factory=list)
    must_fix: list[str] = field(default_factory=list)


def _heuristic_critique(chapter: dict[str, str], content: str) -> TheoryCritique:
    text = content.strip()
    issues: list[str] = []
    must_fix: list[str] = []
    if len(text) < _MIN_CHARS:
        issues.append("theory draft is too short for a teachable chapter")
        must_fix.append("Expand with concrete grounded explanations from the excerpt")
    collapsed = collapse_repeated_prose(text)
    if len(collapsed) < len(text) * 0.72:
        issues.append("draft repeats the same blocks")
        must_fix.append("Remove duplicated sections; keep one clear progression")
    if len(_THROAT_RE.findall(text)) >= 3:
        issues.append("too much throat-clearing / meta intro")
        must_fix.append("Cut filler intros; start teaching from the excerpt")
    excerpt = _as_str(chapter.get("source_excerpt")) or ""
    if len(excerpt) >= 240:
        excerpt_fp = _title_fingerprint(excerpt[:2500])
        draft_fp = _title_fingerprint(text[:5000])
        if excerpt_fp and draft_fp:
            overlap = len(excerpt_fp & draft_fp) / max(1, len(excerpt_fp))
            if overlap < _GROUND_MIN_OVERLAP:
                issues.append("weak grounding on the source excerpt")
                must_fix.append("Reuse key terms and ideas from the excerpt without inventing APIs")
    if not issues:
        return TheoryCritique(ok=True, score=0.8)
    score = max(0.15, 0.7 - 0.12 * len(issues))
    return TheoryCritique(ok=False, score=score, issues=issues, must_fix=must_fix)


def _parse_critique(payload: dict[str, object]) -> TheoryCritique:
    issues_raw = payload.get("issues")
    fixes_raw = payload.get("must_fix")
    issues = (
        [str(item).strip() for item in issues_raw if str(item).strip()][:5]
        if isinstance(issues_raw, list)
        else []
    )
    must_fix = (
        [str(item).strip() for item in fixes_raw if str(item).strip()][:5]
        if isinstance(fixes_raw, list)
        else []
    )
    score_raw = payload.get("score")
    default_score = 0.8 if not must_fix else 0.4
    score = float(score_raw) if isinstance(score_raw, int | float) else default_score
    score = max(0.0, min(1.0, score))
    ok_raw = payload.get("ok")
    ok = bool(ok_raw) if isinstance(ok_raw, bool) else (score >= 0.72 and not must_fix)
    if must_fix:
        ok = False
    if score < 0.72:
        ok = False
    return TheoryCritique(ok=ok, score=score, issues=issues, must_fix=must_fix)


def _merge_critiques(left: TheoryCritique, right: TheoryCritique) -> TheoryCritique:
    issues = list(dict.fromkeys([*left.issues, *right.issues]))[:5]
    must_fix = list(dict.fromkeys([*left.must_fix, *right.must_fix]))[:5]
    score = min(left.score, right.score)
    ok = left.ok and right.ok and score >= 0.72 and not must_fix
    return TheoryCritique(ok=ok, score=score, issues=issues, must_fix=must_fix)


def _soft_fail_critique(heuristic: TheoryCritique) -> TheoryCritique:
    if heuristic.ok:
        return heuristic
    fixes = heuristic.must_fix or [
        "Strengthen grounding on the source excerpt",
        "Improve clarity and chapter objective coverage",
    ]
    return TheoryCritique(
        ok=False,
        score=min(0.55, heuristic.score),
        issues=[*heuristic.issues, "quality critique unavailable"][:5],
        must_fix=fixes[:5],
    )


def _theory_revise_system(target: LlmTarget, *, compact: bool, extra: str) -> str:
    return compose_prompt(
        course_from_article_theory_prose_prompt(
            compact=compact,
            course_profile=get_course_profile(),
            local_runtime=looks_like_ollama_endpoint(target),
            strategy_pack=get_strategy_pack(),
        ),
        extra,
    )


async def _theory_critique(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    content: str,
    outcomes: list[str],
    compact: bool,
) -> tuple[TheoryCritique, bool]:
    heuristic = _heuristic_critique(chapter, content)
    try:
        payload = await _stage_json(
            client,
            target,
            compact=compact,
            stage="quality",
            user_message=_theory_critique_user_message(
                body,
                chapter=chapter,
                content=content,
                outcomes=outcomes,
            ),
            max_tokens=900 if compact else 1200,
        )
    except TutorError:
        return _merge_critiques(heuristic, _soft_fail_critique(heuristic)), True
    llm = _parse_critique(payload if isinstance(payload, dict) else {})
    return _merge_critiques(heuristic, llm), False


async def _revise_theory_content(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    content: str,
    critique: TheoryCritique,
    compact: bool,
) -> str:
    fixes = critique.must_fix or critique.issues or ["Improve grounding and clarity"]
    patched = await complete_text_until_done(
        client,
        target,
        system_prompt=_theory_revise_system(
            target,
            compact=compact,
            extra=(
                "You revise one theory chapter. Apply must_fix. "
                "Ground every claim in the source excerpt. Markdown only."
            ),
        ),
        user_message=_theory_patch_user_message(
            body,
            chapter=chapter,
            content=content,
            must_fix=fixes,
        ),
        max_tokens=(
            COURSE_LLM.theory_section_max_tokens if compact else COURSE_LLM.theory_max_tokens
        ),
        max_continues=2,
        temperature=COURSE_LLM.theory_patch_temperature,
        top_p=0.9,
        num_ctx=target.num_ctx,
    )
    return clean_theory_markdown(patched.strip() or content) or content


async def _emergency_theory_rewrite(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    content: str,
    compact: bool,
) -> str:
    if not (_as_str(chapter.get("source_excerpt")) or ""):
        return content
    emergency = await complete_text_until_done(
        client,
        target,
        system_prompt=_theory_revise_system(
            target,
            compact=compact,
            extra=(
                "Rewrite the theory chapter strictly from the source excerpt. "
                "Do not invent APIs. Markdown only, teach clearly."
            ),
        ),
        user_message=_theory_patch_user_message(
            body,
            chapter=chapter,
            content=content,
            must_fix=[
                "Rebuild the chapter from the excerpt",
                "Keep the chapter learning objective",
            ],
        ),
        max_tokens=2600,
        max_continues=2,
        temperature=0.1,
        top_p=0.85,
        num_ctx=target.num_ctx,
    )
    cleaned = clean_theory_markdown(emergency.strip())
    return cleaned if len(cleaned) > len(content) * 0.6 else content


async def reinforce_theory_chapter(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    step: dict[str, object],
    outcomes: list[str],
    max_rounds: int = 2,
    compact: bool = False,
) -> tuple[dict[str, object], list[str]]:

    if max_rounds <= 0 or not isinstance(target, LlmTarget):
        return step, []
    notes: list[str] = []
    content = str(step.get("content") or "").strip()
    if not content:
        return step, ["theory quality skipped: empty chapter"]

    best_content = content
    best_score = 0.0
    title = str(chapter.get("title") or step.get("title") or "chapter")

    for round_index in range(1, max_rounds + 1):
        critique, soft_failed = await _theory_critique(
            client,
            target,
            body=body,
            chapter=chapter,
            content=content,
            outcomes=outcomes,
            compact=compact,
        )
        if soft_failed:
            notes.append(f"theory quality critique soft-fail: {title} (round {round_index})")
        if critique.score >= best_score:
            best_score = critique.score
            best_content = content
        if critique.ok:
            if content != str(step.get("content") or ""):
                step = {**step, "content": clean_theory_markdown(content)}
            return step, notes

        content = await _revise_theory_content(
            client,
            target,
            body=body,
            chapter=chapter,
            content=content,
            critique=critique,
            compact=compact,
        )

    trailing = _heuristic_critique(chapter, content)
    if trailing.score >= best_score:
        best_content = content
        best_score = trailing.score
    if trailing.ok:
        step = {**step, "content": clean_theory_markdown(content)}
        return step, notes

    emergency = await _emergency_theory_rewrite(
        client,
        target,
        body=body,
        chapter=chapter,
        content=best_content,
        compact=compact,
    )
    if emergency != best_content:
        best_content = emergency
        best_score = max(best_score, 0.55)

    final = _heuristic_critique(chapter, best_content)
    step = {**step, "content": best_content}
    if not final.ok:
        notes.append(
            f"theory quality gate weak after reinforce: {title} "
            f"(score~{best_score:.2f}; {', '.join(final.issues[:2]) or 'unresolved'})"
        )
    return step, notes
