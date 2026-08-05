from __future__ import annotations

import httpx
from app.domain.llm.client import complete_chat_result
from app.domain.llm.prose_dedupe import continuation_is_restart
from app.domain.llm.result import ChatCompletionResult
from app.domain.llm.target import LlmTarget

_CONTINUE_SYSTEM = (
    "You continue unfinished assistant output for Task Studio. "
    "Emit ONLY the missing continuation — no preamble, no restart, no markdown fences "
    "around the whole answer unless the unfinished text already opened one. "
    "Never repeat headings or paragraphs already present in the unfinished text."
)


async def complete_text_until_done(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    max_continues: int = 8,
    temperature: float | None = 0.15,
    top_p: float | None = None,
    num_ctx: int | None = None,
    conversation_id: str | None = None,
) -> str:
    parts: list[str] = []
    history: list[dict[str, str]] | None = None
    current_user = user_message
    current_system = system_prompt
    budget = max(256, max_tokens)

    for step in range(max_continues + 1):
        result = await complete_chat_result(
            client,
            target,
            system_prompt=current_system,
            user_message=current_user,
            history=history,
            conversation_id=conversation_id,
            temperature=temperature,
            top_p=top_p,
            max_tokens=budget,
            num_ctx=num_ctx,
        )
        chunk = result.content
        if not chunk:
            break
        assembled = "".join(parts)
        if assembled and continuation_is_restart(assembled, chunk):
            break
        parts.append(chunk)
        if not result.truncated:
            break
        if step >= max_continues:
            break
        assembled = "".join(parts)
        history = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assembled},
        ]
        current_system = _CONTINUE_SYSTEM
        current_user = (
            "Continue exactly from where you stopped. "
            "Output ONLY the new continuation — do not repeat earlier paragraphs."
        )

    return "".join(parts)


async def complete_json_raw_until_done(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    max_continues: int = 6,
    temperature: float | None = 0.15,
    top_p: float | None = None,
    num_ctx: int | None = None,
) -> ChatCompletionResult:
    from app.domain.json_util.extract import extract_json_object
    from app.domain.llm.json_mode import complete_json_chat_result

    result = await complete_json_chat_result(
        client,
        target,
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        num_ctx=num_ctx,
    )
    raw = result.content
    if extract_json_object(raw) is not None and not result.truncated and not _json_looks_open(raw):
        return result

    for _ in range(max_continues):
        if extract_json_object(raw) is not None and not _json_looks_open(raw):
            return ChatCompletionResult(content=raw, finish_reason="stop", max_tokens=max_tokens)
        if not result.truncated and extract_json_object(raw) is not None:
            return ChatCompletionResult(content=raw, finish_reason="stop", max_tokens=max_tokens)
        cont = await complete_chat_result(
            client,
            target,
            system_prompt=_CONTINUE_SYSTEM,
            user_message=(
                "The previous JSON was cut off. Continue exactly from the cut point. "
                "Output ONLY the missing characters needed to finish ONE JSON object.\n\n"
                f"<json_tail>\n{raw[-1200:]}\n</json_tail>"
            ),
            temperature=0.0,
            top_p=top_p,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
        )
        if not cont.content:
            break
        raw = f"{raw}{cont.content}"
        result = ChatCompletionResult(
            content=raw,
            finish_reason=cont.finish_reason,
            max_tokens=max_tokens,
        )
    return ChatCompletionResult(
        content=raw,
        finish_reason=result.finish_reason,
        max_tokens=max_tokens,
    )


def _json_looks_open(raw: str) -> bool:
    text = (raw or "").strip()
    if not text:
        return True
    depth = 0
    in_string = False
    escape = False
    started = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            started = True
            depth += 1
            continue
        if ch == "}":
            depth = max(0, depth - 1)
    return (not started) or in_string or depth > 0
