from __future__ import annotations

from collections.abc import Mapping

from app.domain.llm.target import LlmTarget

JsonSchema = Mapping[str, object]


def request_headers(target: LlmTarget, *, conversation_id: str | None = None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"
    if conversation_id:
        headers["X-Task-Studio-Conversation-Id"] = conversation_id
    return headers


def looks_like_ollama_endpoint(target: LlmTarget) -> bool:
    base = target.base_url.casefold()
    if "cursor-proxy" in base:
        return False
    return "ollama" in base or ":11434" in base


def chat_payload(
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
    stream: bool,
    history: list[dict[str, str]] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    num_ctx: int | None = None,
    response_format: Mapping[str, object] | None = None,
    json_schema: JsonSchema | None = None,
) -> dict[str, object]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    payload: dict[str, object] = {
        "model": target.model,
        "messages": messages,
        "stream": stream,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if num_ctx is not None and looks_like_ollama_endpoint(target):
        payload["options"] = {"num_ctx": num_ctx}
        payload["keep_alive"] = "-1"
    if json_schema is not None and looks_like_ollama_endpoint(target):
        payload["format"] = dict(json_schema)
    elif response_format is not None:
        payload["response_format"] = dict(response_format)
    elif json_schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": dict(json_schema)},
        }
    return payload


def message_content(body: dict[str, object]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        msg = "empty LLM response"
        raise ValueError(msg)
    first = choices[0]
    if not isinstance(first, dict):
        msg = "invalid LLM response"
        raise ValueError(msg)
    message = first.get("message")
    if not isinstance(message, dict):
        msg = "invalid LLM response"
        raise ValueError(msg)
    content = _coerce_message_content(message.get("content"))
    if not content:
        msg = "empty LLM content"
        raise ValueError(msg)
    return content


def choice_finish_reason(body: dict[str, object]) -> str | None:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    reason = first.get("finish_reason")
    return reason.strip() if isinstance(reason, str) and reason.strip() else None


def _coerce_message_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
                continue
            nested = item.get("content")
            if isinstance(nested, str) and nested.strip():
                parts.append(nested.strip())
        return "\n".join(parts).strip()
    return ""
