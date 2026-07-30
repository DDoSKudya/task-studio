from __future__ import annotations

from typing import Any

import httpx
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .messages import _quiz_one_user_message
from .normalize import _normalize_quizzes
from .stage_llm import _stage_json


def _coerce_quizzes_payload(payload: dict[str, Any]) -> list[object]:
    quizzes = payload.get("quizzes")
    if isinstance(quizzes, list):
        return quizzes
    quiz = payload.get("quiz")
    if isinstance(quiz, dict):
        return [quiz]
    if payload.get("question") and payload.get("choices"):
        return [payload]
    return []


async def generate_quizzes(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    theory_steps: list[dict[str, object]],
) -> list[dict[str, object]]:

    collected: list[dict[str, object]] = []
    count = max(1, int(body.quiz_count))
    for index in range(count):
        prior_titles = [str(item.get("title") or "") for item in collected]
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
            ),
            max_tokens=1200 if compact else 2000,
        )
        batch = _normalize_quizzes(_coerce_quizzes_payload(payload), count=1)
        if not batch:
            raise TutorError(
                status.HTTP_502_BAD_GATEWAY,
                f"course quizzes stage returned no quiz for index={index + 1}",
            )
        collected.append(batch[0])
    if len(collected) < min(3, count):
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course quizzes stage returned too few items")
    return collected
