from __future__ import annotations

import os


def bind_host() -> str:
    return os.getenv("HOST", "0.0.0.0")  # noqa: S104
