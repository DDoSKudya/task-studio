from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CursorProxyConfig:
    port: int
    cursor_api_base: str
    request_timeout_seconds: float
    cleanup_agents: bool


def load_config() -> CursorProxyConfig:
    return CursorProxyConfig(
        port=int(os.getenv("PORT", "8015")),
        cursor_api_base=os.getenv("CURSOR_API_BASE", "https://api.cursor.com").rstrip("/"),
        request_timeout_seconds=float(os.getenv("CURSOR_PROXY_TIMEOUT_SECONDS", "900")),
        cleanup_agents=os.getenv("CURSOR_PROXY_CLEANUP_AGENTS", "true").lower()
        not in {"0", "false", "no"},
    )
