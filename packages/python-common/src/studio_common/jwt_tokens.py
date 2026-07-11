from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt


def create_access_token(
    user_id: uuid.UUID | str,
    *,
    secret: str | None = None,
    expire_hours: int | None = None,
) -> str:
    key = secret or os.environ["JWT_SECRET"]
    hours = expire_hours if expire_hours is not None else int(os.getenv("JWT_EXPIRE_HOURS", "168"))
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=hours),
    }
    return jwt.encode(payload, key, algorithm="HS256")


def decode_user_id(token: str, *, secret: str | None = None) -> uuid.UUID:
    key = secret or os.environ["JWT_SECRET"]
    payload = jwt.decode(token, key, algorithms=["HS256"])
    return uuid.UUID(str(payload["sub"]))
