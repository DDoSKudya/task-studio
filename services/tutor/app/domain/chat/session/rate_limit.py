from __future__ import annotations

from datetime import UTC, datetime

from app.domain.errors import TutorError
from fastapi import status
from redis.asyncio import Redis

_RATE_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


async def check_rate_limits(
    redis: Redis,
    *,
    user_id: str,
    per_minute_limit: int,
    daily_limit: int,
) -> None:
    now = datetime.now(UTC)
    minute_key = f"rate:tutor:{user_id}:{now.strftime('%Y%m%d%H%M')}"
    minute_count = int(await redis.eval(_RATE_SCRIPT, 1, minute_key, 60))
    if minute_count > per_minute_limit:
        raise TutorError(status.HTTP_429_TOO_MANY_REQUESTS, "rate limit exceeded")

    if daily_limit <= 0:
        return

    day_key = f"rate:tutor:daily:{user_id}:{now.strftime('%Y%m%d')}"
    day_count = int(await redis.eval(_RATE_SCRIPT, 1, day_key, 86_400))
    if day_count > daily_limit:
        raise TutorError(status.HTTP_429_TOO_MANY_REQUESTS, "daily limit exceeded")
