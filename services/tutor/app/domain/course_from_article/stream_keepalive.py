from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Coroutine

from app.domain.errors import TutorError
from fastapi import status

from .constants import _COURSE_STREAM_PING_SECONDS
from .progress_events import _sse_event


def _spawn[T](coro: Coroutine[object, object, T]) -> asyncio.Task[T]:
    return asyncio.create_task(coro)


async def iter_course_sse_with_pings(
    events: AsyncIterator[dict[str, object]],
) -> AsyncIterator[bytes]:
    """Keep nginx/proxy SSE alive during long Ollama waits without stage events."""
    agen = events.__aiter__()

    async def _next() -> dict[str, object]:
        return await agen.__anext__()

    pending = _spawn(_next())
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=_COURSE_STREAM_PING_SECONDS)
            if not done:
                yield _sse_event({"type": "ping"})
                continue
            try:
                event = pending.result()
            except StopAsyncIteration:
                break
            except asyncio.CancelledError:
                raise
            yield _sse_event(event)
            pending = _spawn(_next())
    except asyncio.CancelledError:
        raise
    except TutorError as exc:
        yield _sse_event(
            {
                "type": "error",
                "stage": "failed",
                "status": "error",
                "progress": 0.0,
                "message": exc.detail,
                "status_code": exc.status_code,
            }
        )
    except Exception as exc:  # noqa: BLE001
        yield _sse_event(
            {
                "type": "error",
                "stage": "failed",
                "status": "error",
                "progress": 0.0,
                "message": str(exc) or "course generation failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }
        )
    finally:
        # Abort in-flight LLM await so course pipeline can unload Ollama.
        if not pending.done():
            pending.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pending
