from __future__ import annotations

import uuid
from typing import Annotated

import httpx
from app.config import TutorConfig
from fastapi import Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis


def get_config(request: Request) -> TutorConfig:
    return request.app.state.tutor_config


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.tutor_http_client


def get_redis(request: Request) -> Redis:
    redis: Redis | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="redis unavailable",
        )
    return redis


def get_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> uuid.UUID:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing user id")
    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid user id",
        ) from exc


type ConfigDep = Annotated[TutorConfig, Depends(get_config)]
type ClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
type RedisDep = Annotated[Redis, Depends(get_redis)]
type UserId = Annotated[uuid.UUID, Depends(get_user_id)]
