from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True, slots=True)
class StudioApiSettings:
    auth_service_url: str
    catalog_service_url: str
    media_service_url: str
    jwt_secret: str
    jwt_expire_hours: int
    cookie_name: str
    cookie_secure: bool


def load_settings() -> StudioApiSettings:
    return StudioApiSettings(
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth:8001").rstrip("/"),
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        media_service_url=os.getenv("MEDIA_SERVICE_URL", "http://media:8009").rstrip("/"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-change-me"),
        jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "168")),
        cookie_name=os.getenv("AUTH_COOKIE_NAME", "studio_access_token"),
        cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    )


def get_settings(request: Request) -> StudioApiSettings:
    return request.app.state.settings
