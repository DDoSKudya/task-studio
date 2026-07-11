from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True, slots=True)
class StudioApiSettings:
    auth_service_url: str
    catalog_service_url: str
    media_service_url: str
    sessions_service_url: str
    tutor_service_url: str
    orchestrator_service_url: str
    jwt_secret: str
    jwt_expire_hours: int
    cookie_name: str
    cookie_secure: bool
    secrets_master_key: str | None
    lsp_pyright_host: str
    lsp_pyright_port: int
    lsp_typescript_host: str
    lsp_typescript_port: int
    lsp_gopls_host: str
    lsp_gopls_port: int
    lsp_sqls_host: str
    lsp_sqls_port: int


def load_settings() -> StudioApiSettings:
    return StudioApiSettings(
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth:8001").rstrip("/"),
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        media_service_url=os.getenv("MEDIA_SERVICE_URL", "http://media:8009").rstrip("/"),
        sessions_service_url=os.getenv("SESSIONS_SERVICE_URL", "http://sessions:8003").rstrip("/"),
        tutor_service_url=os.getenv("TUTOR_SERVICE_URL", "http://tutor:8006").rstrip("/"),
        orchestrator_service_url=os.getenv(
            "ORCHESTRATOR_SERVICE_URL",
            "http://orchestrator:8011",
        ).rstrip("/"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-change-me"),
        jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "168")),
        cookie_name=os.getenv("AUTH_COOKIE_NAME", "studio_access_token"),
        cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        secrets_master_key=os.getenv("SECRETS_MASTER_KEY"),
        lsp_pyright_host=os.getenv("LSP_PYRIGHT_HOST", "lsp-pyright"),
        lsp_pyright_port=int(os.getenv("LSP_PYRIGHT_PORT", "3000")),
        lsp_typescript_host=os.getenv("LSP_TYPESCRIPT_HOST", "lsp-typescript"),
        lsp_typescript_port=int(os.getenv("LSP_TYPESCRIPT_PORT", "3000")),
        lsp_gopls_host=os.getenv("LSP_GOPLS_HOST", "lsp-gopls"),
        lsp_gopls_port=int(os.getenv("LSP_GOPLS_PORT", "3000")),
        lsp_sqls_host=os.getenv("LSP_SQLS_HOST", "lsp-sqls"),
        lsp_sqls_port=int(os.getenv("LSP_SQLS_PORT", "3000")),
    )


def get_settings(request: Request) -> StudioApiSettings:
    return request.app.state.settings
