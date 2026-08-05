from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

_WEAK_JWT = frozenset({"", "dev-only-change-me", "change-me", "secret"})


def allow_insecure_defaults() -> bool:
    if os.getenv("ALLOW_INSECURE_DEFAULTS", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return os.getenv("APP_ENV", "").strip().lower() in {"development", "dev", "test"}


def system_token_from_env() -> str:
    return os.getenv("ORCHESTRATOR_SYSTEM_TOKEN", "").strip()


def system_token_headers(token: str | None = None) -> dict[str, str]:
    value = (token if token is not None else system_token_from_env()).strip()
    if not value:
        return {}
    return {"X-System-Token": value}


def require_system_token(
    x_system_token: Annotated[str | None, Header(alias="X-System-Token")] = None,
) -> None:
    expected = system_token_from_env()
    if not expected or x_system_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid system token",
        )


def verify_system_token(
    x_system_token: Annotated[str | None, Header(alias="X-System-Token")] = None,
) -> None:
    expected = system_token_from_env()
    if not expected:
        if allow_insecure_defaults():
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="system token not configured",
        )
    if x_system_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid system token",
        )


def resolve_jwt_secret(raw: str | None = None) -> str:
    secret = (raw if raw is not None else os.getenv("JWT_SECRET", "")).strip()
    if secret and secret not in _WEAK_JWT:
        return secret
    if allow_insecure_defaults():
        return secret or "dev-only-change-me"
    raise RuntimeError("JWT_SECRET must be set to a strong value")


type SystemAuth = Annotated[None, Depends(require_system_token)]
type SystemAuthRelaxed = Annotated[None, Depends(verify_system_token)]
