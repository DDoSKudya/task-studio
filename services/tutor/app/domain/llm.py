from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
from app.config import TutorConfig
from studio_common.crypto import decrypt_bytes


@dataclass(frozen=True, slots=True)
class LlmTarget:
    base_url: str
    api_key: str | None
    model: str


def resolve_llm_target(
    config: TutorConfig,
    *,
    provider_url: str | None,
    api_key_encrypted: str | None,
    model: str | None,
) -> LlmTarget | None:
    resolved_model = model or config.ollama_model
    api_key = _decrypt_api_key(config.secrets_master_key, api_key_encrypted)

    if provider_url:
        return LlmTarget(provider_url.rstrip("/"), api_key, resolved_model)
    if config.default_provider_url:
        return LlmTarget(config.default_provider_url, api_key, resolved_model)
    if config.ollama_url:
        return LlmTarget(f"{config.ollama_url}/v1", None, resolved_model)
    return None


def _decrypt_api_key(master_key: str | None, encrypted_b64: str | None) -> str | None:
    if not encrypted_b64 or not master_key:
        return None
    try:
        payload = base64.b64decode(encrypted_b64)
        return decrypt_bytes(payload, key_b64=master_key).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _request_headers(target: LlmTarget) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"
    return headers


def _chat_payload(
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
    stream: bool,
) -> dict[str, object]:
    return {
        "model": target.model,
        "stream": stream,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }


def _message_content(body: dict[str, object]) -> str:
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
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        msg = "empty LLM content"
        raise ValueError(msg)
    return content.strip()


async def complete_chat_completion(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
) -> str:
    url = f"{target.base_url}/chat/completions"
    response = await client.post(
        url,
        headers=_request_headers(target),
        json=_chat_payload(
            target,
            system_prompt=system_prompt,
            user_message=user_message,
            stream=False,
        ),
        timeout=120.0,
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        msg = "invalid LLM response"
        raise ValueError(msg)
    return _message_content(body)


async def stream_chat_completion(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    system_prompt: str,
    user_message: str,
) -> AsyncIterator[str]:
    url = f"{target.base_url}/chat/completions"
    async with client.stream(
        "POST",
        url,
        headers=_request_headers(target),
        json=_chat_payload(
            target,
            system_prompt=system_prompt,
            user_message=user_message,
            stream=True,
        ),
        timeout=120.0,
    ) as response:
        if response.is_error:
            body = await response.aread()
            raise httpx.HTTPStatusError(
                body.decode("utf-8", errors="replace"),
                request=response.request,
                response=response,
            )
        async for line in response.aiter_lines():
            if chunk := _parse_sse_line(line):
                yield chunk


def _parse_sse_line(line: str) -> str | None:
    if not line.startswith("data:"):
        return None
    data = line.removeprefix("data:").strip()
    if not data or data == "[DONE]":
        return None
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    delta = first.get("delta")
    if not isinstance(delta, dict):
        return None
    content = delta.get("content")
    return content if isinstance(content, str) and content else None
