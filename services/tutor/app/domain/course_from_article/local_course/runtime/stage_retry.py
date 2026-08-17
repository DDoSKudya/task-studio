from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.domain.errors import TutorError

logger = logging.getLogger(__name__)

_PERMANENT_MARKERS = (
    "no source excerpt",
    "no teachable",
    "requires at least",
    "below qwen2.5:7b",
)


async def retry_local_stage[T](
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int,
    label: str,
    title: str,
    delay_seconds: float = 0.8,
) -> T:

    last: TutorError | None = None
    attempts = max(0, retries) + 1
    for attempt in range(attempts):
        try:
            return await operation()
        except asyncio.CancelledError:
            raise
        except TutorError as exc:
            last = exc
            detail = str(exc.detail).casefold()
            if attempt + 1 >= attempts or any(marker in detail for marker in _PERMANENT_MARKERS):
                raise
            logger.warning(
                "local %s for «%s» attempt %s/%s failed: %s; retrying",
                label,
                title,
                attempt + 1,
                attempts,
                exc.detail,
            )
            await asyncio.sleep(min(4.0, delay_seconds * (2**attempt)))
    assert last is not None
    raise last
