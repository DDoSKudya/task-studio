from __future__ import annotations

import httpx
from app.config import TutorConfig
from app.domain.chat.session.models import TutorView, complete_bound_chat
from app.domain.course.cache import format_course_outline, format_step_context, parse_hint_lines
from app.domain.llm import LlmTarget, is_ollama_target
from app.domain.ollama.defaults import OLLAMA_NUM_CTX
from app.domain.prompt_compose import context_budget, hints_system_prompt, step_looks_like_sql


async def generate_contextual_hints(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    config: TutorConfig,
    view: TutorView,
    page: str,
) -> list[str]:
    compact = is_ollama_target(config, target)
    budget = context_budget(compact=compact)
    sql_aware = step_looks_like_sql(view.step)
    system_prompt = hints_system_prompt(
        step_kind=view.step.kind,
        step_title=view.step.title,
        compact=compact,
        sql_aware=sql_aware,
    ) or (
        "Return 2-3 short study hints as a bullet list. "
        "No full solutions, no exact quiz answers. Language: match the course text."
    )
    user_message = "\n\n".join(
        [
            format_course_outline(view.digest, max_steps=budget.outline_steps),
            format_step_context(
                view.digest,
                view.step,
                page_limit=budget.page_chars,
                starter_limit=budget.starter_chars,
            ),
            f"## Extra page text\n{page[: budget.page_chars]}" if page else "",
            "## Request\nProduce hints now.",
            "## Output\nExactly 2 or 3 bullet hints. No preamble.",
        ]
    ).strip()
    raw = await complete_bound_chat(
        client,
        target,
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.35 if compact else None,
        top_p=0.9 if compact else None,
        max_tokens=256 if compact else None,
        num_ctx=OLLAMA_NUM_CTX if compact else None,
    )
    return parse_hint_lines(raw)
