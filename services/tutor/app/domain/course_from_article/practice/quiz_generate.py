from __future__ import annotations

import httpx
from app.domain.course_from_article.common.content.messages import _quiz_one_user_message
from app.domain.course_from_article.common.content.normalize import _normalize_quizzes
from app.domain.course_from_article.common.content.textutil import _slug
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_from_article.common.runtime.stage_llm import _stage_json
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_from_article.quality.assess_quality import quiz_is_usable, reinforce_quiz
from app.domain.errors import TutorError
from app.domain.llm.transport.retry import should_retry_json_error
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


def _coerce_quizzes_payload(payload: dict[str, object]) -> list[object]:
    quizzes = payload.get("quizzes")
    if isinstance(quizzes, list):
        return quizzes
    quiz = payload.get("quiz")
    if isinstance(quiz, dict):
        return [quiz]
    if payload.get("question") and payload.get("choices"):
        return [payload]
    return []


def _choices_from_seed_body(body: str) -> list[str] | None:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    choices: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped[:1] in {"-", "*", "•"}:
            text = stripped[1:].strip()
        elif (
            len(stripped) > 2
            and stripped[1] in ").:"
            and (stripped[0].isalpha() or stripped[0].isdigit())
        ):
            text = stripped[2:].strip()
        else:
            continue
        if text:
            choices.append(text[:200])
        if len(choices) >= 4:
            break
    return None if len(choices) < 4 else choices[:4]


def _quiz_from_seed(seed: HarvestedExercise, index: int) -> dict[str, object] | None:
    choices = _choices_from_seed_body(seed.body)
    if choices is None:
        return None
    title = seed.title.strip() or f"Check {index + 1}"
    question = seed.body.strip().split("\n", maxsplit=1)[0][:400] or title
    if len(question) < 24:
        question = f"{title}: {question}".strip()[:400]
    return {
        "id": _slug(f"quiz-harvest-{index + 1}"),
        "kind": "quiz",
        "title": title[:120],
        "question": question,
        "choices": choices,
        "answer": 0,
    }


def _fallback_quizzes_from_seeds(
    exercise_seeds: list[HarvestedExercise] | None,
    *,
    count: int,
) -> list[dict[str, object]]:
    if not exercise_seeds:
        return []
    quiz_seeds = [item for item in exercise_seeds if item.kind in {"quiz", "open"}]
    picked = quiz_seeds or list(exercise_seeds)
    built: list[dict[str, object]] = []
    for index, seed in enumerate(picked):
        quiz = _quiz_from_seed(seed, index)
        if quiz is None:
            continue
        built.append(quiz)
        if len(built) >= count:
            break
    return built


def _quiz_question_key(quiz: dict[str, object]) -> str:
    return str(quiz.get("question") or "").strip().casefold()


async def _request_quiz(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None,
    index: int,
    prior_titles: list[str],
    max_attempts: int,
    token_budget: int,
) -> dict[str, object] | None:
    for attempt in range(max_attempts):
        try:
            payload = await _stage_json(
                client,
                target,
                compact=compact,
                stage="quizzes",
                user_message=_quiz_one_user_message(
                    body,
                    outcomes=outcomes,
                    chapters=chapters,
                    theory_steps=theory_steps,
                    index=index,
                    prior_titles=prior_titles,
                    exercise_seeds=exercise_seeds,
                ),
                max_tokens=token_budget,
            )
        except TutorError as exc:
            if not should_retry_json_error(exc, attempt=attempt, attempts=max_attempts):
                raise
            continue
        batch = _normalize_quizzes(_coerce_quizzes_payload(payload), count=1)
        if batch:
            return batch[0]
    return None


async def _reinforce_generated_quiz(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    quiz: dict[str, object],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    quality_rounds: int,
    compact: bool,
    notes: list[str],
) -> dict[str, object]:
    if quality_rounds <= 0:
        return quiz
    reinforced, reinforce_notes = await reinforce_quiz(
        client,
        target,
        body=body,
        quiz=quiz,
        chapters=chapters,
        outcomes=outcomes,
        theory_steps=theory_steps,
        max_rounds=quality_rounds,
        compact=compact,
    )
    notes.extend(reinforce_notes)
    return reinforced


async def generate_quizzes(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None = None,
    fail_soft: bool = False,
    max_attempts: int = COURSE_LLM.max_quiz_attempts,
    max_tokens: int | None = None,
    warnings: list[str] | None = None,
    quality_rounds: int = 0,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    seen_questions: set[str] = set()
    notes = warnings if warnings is not None else []
    count = max(1, int(body.quiz_count))
    token_budget = (
        max_tokens if max_tokens is not None else (1200 if compact else COURSE_LLM.quiz_max_tokens)
    )
    for index in range(count):
        prior_titles = [str(item.get("title") or "") for item in collected]
        quiz = await _request_quiz(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            exercise_seeds=exercise_seeds,
            index=index,
            prior_titles=prior_titles,
            max_attempts=max_attempts,
            token_budget=token_budget,
        )
        if quiz is None:
            continue
        quiz = await _reinforce_generated_quiz(
            client,
            target,
            body=body,
            quiz=quiz,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            quality_rounds=quality_rounds,
            compact=compact,
            notes=notes,
        )
        if not quiz_is_usable(quiz):
            notes.append(
                f"quizzes: dropped unusable item after reinforce "
                f"({quiz.get('id') or quiz.get('title') or index + 1})"
            )
            continue
        if question := _quiz_question_key(quiz):
            if question in seen_questions:
                continue
            seen_questions.add(question)
        collected.append(quiz)
    if collected:
        return collected
    if not fail_soft:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course quizzes stage returned no quizzes")
    fallback = _fallback_quizzes_from_seeds(exercise_seeds, count=min(count, 1))
    if warnings is not None:
        warnings.append(
            "quizzes: LLM returned none; using harvested article checks as fallback"
            if fallback
            else "quizzes: LLM returned none; continuing without quizzes"
        )
    if not fallback:
        return []
    reinforced: list[dict[str, object]] = []
    for quiz in fallback:
        item = await _reinforce_generated_quiz(
            client,
            target,
            body=body,
            quiz=quiz,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            quality_rounds=quality_rounds,
            compact=compact,
            notes=notes,
        )
        if quiz_is_usable(item):
            reinforced.append(item)
    if not reinforced and warnings is not None:
        warnings.append(
            "quizzes: harvest fallback unusable after reinforce; continuing without quizzes"
        )
    return reinforced
