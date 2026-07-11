from __future__ import annotations

import uuid
from typing import Literal, assert_never

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel

type ServiceMethod = Literal["get", "post", "patch", "delete"]


def upstream_detail(response: httpx.Response) -> str | list[dict[str, object]]:
    try:
        payload = response.json()
    except ValueError:
        return "upstream error"
    if not isinstance(payload, dict):
        return "upstream error"
    detail = payload.get("detail", "upstream error")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return detail
    return "upstream error"


def raise_for_upstream_error(response: httpx.Response) -> None:
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail=upstream_detail(response))


async def call_service(
    client: httpx.AsyncClient,
    base_url: str,
    method: ServiceMethod,
    path: str,
    *,
    user_id: uuid.UUID | None = None,
    json: dict[str, object] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> httpx.Response:
    url = f"{base_url}{path}"
    headers = {"X-User-Id": str(user_id)} if user_id is not None else None
    match method:
        case "get":
            return await client.get(url, headers=headers)
        case "post":
            return await client.post(url, headers=headers, json=json, files=files)
        case "patch":
            return await client.patch(url, headers=headers, json=json)
        case "delete":
            return await client.delete(url, headers=headers)
        case unreachable:
            assert_never(unreachable)


def parse_upstream[T: BaseModel](response: httpx.Response, model: type[T]) -> T:
    raise_for_upstream_error(response)
    return model.model_validate(response.json())


def parse_upstream_list[T: BaseModel](response: httpx.Response, model: type[T]) -> list[T]:
    raise_for_upstream_error(response)
    payload = response.json()
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="invalid upstream response",
        )
    return [model.model_validate(item) for item in payload]
