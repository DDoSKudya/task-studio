from __future__ import annotations

import httpx
from app.domain.course_from_article.common.content.normalize import (
    _normalize_code_tasks,
    _normalize_open_tasks,
    _normalize_quizzes,
)
from app.domain.course_from_article.common.content.textutil import _as_str
from app.domain.course_from_article.common.runtime.stage_llm import _stage_json
from app.domain.course_from_article.quality.chapter_quality import (
    TheoryCritique,
    _merge_critiques,
    _parse_critique,
    _soft_fail_critique,
)
from app.domain.course_from_article.quality.messages_quality import (
    _practice_critique_user_message,
    _practice_patch_user_message,
    _quiz_critique_user_message,
    _quiz_patch_user_message,
)
from app.domain.course_strategies import (
    choice_is_placeholder,
    question_embeds_choices,
    stem_wants_many_answers,
)
from app.domain.errors import TutorError
from app.domain.llm import LlmTarget
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

_GENERIC_QUIZ_CHOICES = {
    "matches the article",
    "opposite of the article",
    "unrelated detail",
    "too vague to verify",
}


def quiz_is_usable(quiz: dict[str, object]) -> bool:
    return _heuristic_quiz(quiz).ok


def _heuristic_quiz(quiz: dict[str, object]) -> TheoryCritique:
    issues: list[str] = []
    must_fix: list[str] = []
    question = str(quiz.get("question") or "").strip()
    choices_raw = quiz.get("choices")
    choices = (
        [str(item).strip() for item in choices_raw if str(item).strip()]
        if isinstance(choices_raw, list)
        else []
    )
    answer = quiz.get("answer")
    if len(question) < 24:
        issues.append("question stem is too short or vague")
        must_fix.append("Rewrite a concrete stem grounded in the theory")
    if len(choices) < 4:
        issues.append("need four distinct choices")
        must_fix.append("Provide exactly four distinct answer choices")
    elif len(set(choice.casefold() for choice in choices)) < 4:
        issues.append("choices are duplicated")
        must_fix.append("Make all four choices distinct and plausible")
    if not isinstance(answer, int) or not 0 <= answer <= 3:
        issues.append("answer index is missing or invalid")
        must_fix.append("Set answer to the correct choice index 0..3")
    choice_blob = " ".join(choices).casefold()
    if sum(1 for token in _GENERIC_QUIZ_CHOICES if token in choice_blob) >= 3:
        issues.append("choices look like harvest placeholder options")
        must_fix.append("Replace placeholder choices with content from the theory")
    if any(choice_is_placeholder(choice) for choice in choices):
        issues.append("choices copy the prompt example placeholders")
        must_fix.append('Write real answer texts; never emit "full text …" or "option A"')
    if stem_wants_many_answers(question):
        issues.append("stem asks for several correct answers")
        must_fix.append("Ask for exactly one correct answer")
    if question_embeds_choices(question, choices):
        issues.append("stem repeats the answer list")
        must_fix.append("Keep the choices out of the question stem")
    if not issues:
        return TheoryCritique(ok=True, score=0.82)
    score = max(0.15, 0.7 - 0.12 * len(issues))
    return TheoryCritique(ok=False, score=score, issues=issues, must_fix=must_fix)


def _heuristic_practice(task: dict[str, object], *, kind: str) -> TheoryCritique:
    issues: list[str] = []
    must_fix: list[str] = []
    title = str(task.get("title") or "").strip()
    content = str(task.get("content") or "").strip()
    if len(title) < 8:
        issues.append("title is too thin")
        must_fix.append("Write a specific practice title")
    if len(content) < 40:
        issues.append("brief is too short")
        must_fix.append("Expand the learner brief with concrete steps")
    if kind == "code":
        template = str(task.get("template") or "").strip()
        if len(template) < 20:
            issues.append("code template is empty or tiny")
            must_fix.append("Provide a non-empty starter template")
        tests = task.get("tests")
        checker = str(task.get("checker") or "").casefold()
        has_tests = isinstance(tests, list) and bool(tests)
        if not has_tests and checker != "llm":
            issues.append("no executable tests and no llm checker")
            must_fix.append('Add tests or set checker to "llm" with a short rubric')
    if title.casefold().startswith("practice (") and "the article" in content.casefold():
        issues.append("scaffold-looking generic practice")
        must_fix.append("Ground the task in the chapter topic, not a generic scaffold")
    if not issues:
        return TheoryCritique(ok=True, score=0.82)
    score = max(0.15, 0.7 - 0.12 * len(issues))
    return TheoryCritique(ok=False, score=score, issues=issues, must_fix=must_fix)


def _quiz_context_blob(
    *,
    chapters: list[dict[str, str]],
    theory_steps: list[dict[str, object]],
) -> str:
    bits: list[str] = []
    for chapter in chapters[:3]:
        title = chapter.get("title") or ""
        excerpt = (_as_str(chapter.get("source_excerpt")) or "")[:900]
        bits.append(f"### {title}\n{excerpt}")
    for step in theory_steps[:2]:
        bits.append(str(step.get("content") or "")[:1200])
    return "\n\n".join(bits)[:4500]


def _coerce_quiz_payload(payload: dict[str, object]) -> list[object]:
    quizzes = payload.get("quizzes")
    if isinstance(quizzes, list):
        return quizzes
    quiz = payload.get("quiz")
    if isinstance(quiz, dict):
        return [quiz]
    if payload.get("question") and payload.get("choices"):
        return [payload]
    return []


def _coerce_task_payload(payload: dict[str, object]) -> list[object]:
    tasks = payload.get("tasks")
    if isinstance(tasks, list):
        return tasks
    task = payload.get("task")
    if isinstance(task, dict):
        return [task]
    if payload.get("content") or payload.get("template"):
        return [payload]
    return []


async def reinforce_quiz(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    quiz: dict[str, object],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    max_rounds: int = 2,
    compact: bool = False,
) -> tuple[dict[str, object], list[str]]:
    if max_rounds <= 0 or not isinstance(target, LlmTarget):
        return quiz, []
    notes: list[str] = []
    current = dict(quiz)
    best = dict(quiz)
    best_score = 0.0
    label = str(quiz.get("title") or quiz.get("id") or "quiz")
    context = _quiz_context_blob(chapters=chapters, theory_steps=theory_steps)

    for round_index in range(1, max_rounds + 1):
        heuristic = _heuristic_quiz(current)
        if heuristic.ok:
            return current, notes
        if _quiz_placeholder_heavy(heuristic):
            llm = heuristic
        else:
            try:
                payload = await _stage_json(
                    client,
                    target,
                    compact=compact,
                    stage="quality",
                    user_message=_quiz_critique_user_message(
                        body,
                        quiz=current,
                        outcomes=outcomes,
                        context=context,
                    ),
                    max_tokens=800 if compact else 1100,
                )
                llm = _parse_critique(payload if isinstance(payload, dict) else {})
            except TutorError:
                llm = _soft_fail_critique(heuristic)
                notes.append(f"quiz quality critique soft-fail: {label} (round {round_index})")
        critique = _merge_critiques(heuristic, llm)
        if critique.score >= best_score:
            best_score = critique.score
            best = dict(current)
        if critique.ok:
            return current, notes

        fixes = critique.must_fix or critique.issues or ["Improve grounding and clarity"]
        try:
            patched = await _stage_json(
                client,
                target,
                compact=compact,
                stage="quality",
                user_message=_quiz_patch_user_message(
                    body,
                    quiz=current,
                    must_fix=fixes,
                    context=context,
                ),
                max_tokens=1000 if compact else 1400,
            )
        except TutorError:
            notes.append(f"quiz quality patch soft-fail: {label} (round {round_index})")
            break
        batch = _normalize_quizzes(
            _coerce_quiz_payload(patched if isinstance(patched, dict) else {}),
            count=1,
        )
        if batch:
            rebuilt = dict(batch[0])
            rebuilt["id"] = current.get("id") or rebuilt.get("id")
            if current.get("chapter_id"):
                rebuilt["chapter_id"] = current["chapter_id"]
            current = rebuilt

    trailing = _heuristic_quiz(current)
    if trailing.ok:
        return current, notes
    if trailing.score >= best_score:
        best = dict(current)
        best_score = trailing.score
    final = _heuristic_quiz(best)
    if not final.ok:
        notes.append(
            f"quiz quality gate weak after reinforce: {label} "
            f"(score~{best_score:.2f}; {', '.join(final.issues[:2]) or 'unresolved'})"
        )
    return best, notes


def _quiz_placeholder_heavy(heuristic: TheoryCritique) -> bool:
    return any("placeholder" in issue for issue in heuristic.issues)


async def _practice_critique(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    task: dict[str, object],
    outcomes: list[str],
    context: str,
    kind: str,
    compact: bool,
) -> tuple[TheoryCritique, bool]:
    heuristic = _heuristic_practice(task, kind=kind)
    try:
        payload = await _stage_json(
            client,
            target,
            compact=compact,
            stage="quality",
            user_message=_practice_critique_user_message(
                body,
                task=task,
                outcomes=outcomes,
                context=context,
                kind=kind,
            ),
            max_tokens=800 if compact else 1100,
        )
    except TutorError:
        return _merge_critiques(heuristic, _soft_fail_critique(heuristic)), True
    llm = _parse_critique(payload if isinstance(payload, dict) else {})
    return _merge_critiques(heuristic, llm), False


def _normalize_rebuilt_practice(
    payload: dict[str, object],
    *,
    current: dict[str, object],
    kind: str,
    runtime: str,
    runtime_version: str,
) -> dict[str, object]:
    if kind == "code":
        batch = _normalize_code_tasks(
            _coerce_task_payload(payload),
            count=1,
            runtime=runtime,
            runtime_version=runtime_version,
        )
    else:
        batch = _normalize_open_tasks(_coerce_task_payload(payload), count=1)
    if not batch:
        return current
    rebuilt = dict(batch[0])
    rebuilt["id"] = current.get("id") or rebuilt.get("id")
    if current.get("level") is not None:
        rebuilt["level"] = current["level"]
    if current.get("chapter_id"):
        rebuilt["chapter_id"] = current["chapter_id"]
    return rebuilt


async def _patch_practice(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    current: dict[str, object],
    critique: TheoryCritique,
    context: str,
    kind: str,
    compact: bool,
    runtime: str,
    runtime_version: str,
) -> dict[str, object]:
    fixes = critique.must_fix or critique.issues or ["Improve grounding and clarity"]
    patched = await _stage_json(
        client,
        target,
        compact=compact,
        stage="quality",
        user_message=_practice_patch_user_message(
            body,
            task=current,
            must_fix=fixes,
            context=context,
            kind=kind,
        ),
        max_tokens=1400 if compact else 2200,
    )
    return _normalize_rebuilt_practice(
        patched if isinstance(patched, dict) else {},
        current=current,
        kind=kind,
        runtime=runtime,
        runtime_version=runtime_version,
    )


async def reinforce_practice_task(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    task: dict[str, object],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    kind: str,
    max_rounds: int = 2,
    compact: bool = False,
    theory_steps: list[dict[str, object]] | None = None,
) -> tuple[dict[str, object], list[str]]:
    if max_rounds <= 0 or not isinstance(target, LlmTarget):
        return task, []
    notes: list[str] = []
    current = dict(task)
    best = dict(task)
    best_score = 0.0
    label = str(task.get("title") or task.get("id") or kind)
    context = _quiz_context_blob(chapters=chapters, theory_steps=theory_steps or [])
    runtime = str(task.get("runtime") or body.runtime or "")
    runtime_version = body.runtime_version or ""

    for round_index in range(1, max_rounds + 1):
        critique, soft_failed = await _practice_critique(
            client,
            target,
            body=body,
            task=current,
            outcomes=outcomes,
            context=context,
            kind=kind,
            compact=compact,
        )
        if soft_failed:
            notes.append(f"practice quality critique soft-fail: {label} (round {round_index})")
        if critique.score >= best_score:
            best_score = critique.score
            best = dict(current)
        if critique.ok:
            return current, notes

        try:
            current = await _patch_practice(
                client,
                target,
                body=body,
                current=current,
                critique=critique,
                context=context,
                kind=kind,
                compact=compact,
                runtime=runtime,
                runtime_version=runtime_version,
            )
        except TutorError:
            notes.append(f"practice quality patch soft-fail: {label} (round {round_index})")
            break

    trailing = _heuristic_practice(current, kind=kind)
    if trailing.ok:
        return current, notes
    if trailing.score >= best_score:
        best = dict(current)
        best_score = trailing.score
    final = _heuristic_practice(best, kind=kind)
    if not final.ok:
        notes.append(
            f"practice quality gate weak after reinforce: {label} "
            f"(score~{best_score:.2f}; {', '.join(final.issues[:2]) or 'unresolved'})"
        )
    return best, notes
