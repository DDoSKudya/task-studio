from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

COURSE_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


def course_stream_response(events: AsyncIterator[bytes | str]) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers=COURSE_STREAM_HEADERS,
    )
