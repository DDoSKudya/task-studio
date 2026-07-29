from __future__ import annotations

import httpx
from app.config import TutorConfig
from app.domain.grade.message import as_str, build_grade_user_message, looks_like_sql
from app.domain.grade.payload import normalize_grade_payload
from app.domain.json_util.repair import parse_or_repair_json
from app.domain.llm import LlmTarget, complete_chat_completion, is_ollama_target
from app.domain.ollama.defaults import OLLAMA_NUM_CTX
from app.domain.prompt_compose import grade_system_prompt
from studio_contracts.tutor_schemas import TutorGradeRequest, TutorGradeResponse


async def grade_via_llm(
    client: httpx.AsyncClient,
    config: TutorConfig,
    target: LlmTarget,
    body: TutorGradeRequest,
) -> TutorGradeResponse:
    compact = is_ollama_target(config, target)
    step = body.step
    kind = body.kind if body.kind in {"quiz", "code", "task", "lab"} else "task"
    title = as_str(step.get("title")) or as_str(step.get("step_title")) or "step"
    sql_aware = kind == "code" and looks_like_sql(step, body.submission)
    system_prompt = grade_system_prompt(
        step_kind=kind,
        step_title=title,
        compact=compact,
        sql_aware=sql_aware,
    )
    user_message = build_grade_user_message(kind=kind, step=step, submission=body.submission)
    try:
        raw = await complete_chat_completion(
            client,
            target,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1 if compact else 0.0,
            top_p=0.9 if compact else None,
            max_tokens=320 if compact else 500,
            num_ctx=OLLAMA_NUM_CTX if compact else None,
        )
    except (httpx.HTTPError, ValueError, TypeError):
        return TutorGradeResponse(
            passed=False,
            confidence=0.0,
            feedback="LLM grader failed",
            usable=False,
            model=target.model,
        )

    repaired = await parse_or_repair_json(
        client,
        target,
        raw=raw,
        hint="grade_check: JSON with passed, confidence, feedback, rationale",
        max_tokens=400 if compact else 600,
        num_ctx=OLLAMA_NUM_CTX if compact else None,
    )
    parsed = normalize_grade_payload(repaired) if repaired else None
    if parsed is None:
        return TutorGradeResponse(
            passed=False,
            confidence=0.0,
            feedback="LLM grader returned unusable output",
            rationale=raw[:400],
            usable=False,
            model=target.model,
        )
    return TutorGradeResponse(
        passed=parsed["passed"],
        confidence=parsed["confidence"],
        feedback=parsed["feedback"],
        rationale=parsed["rationale"],
        usable=True,
        model=target.model,
    )
