from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

                                                                                 
TUTOR_LLM_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)
COURSE_FROM_ARTICLE_TIMEOUT = httpx.Timeout(connect=10.0, read=900.0, write=120.0, pool=10.0)


async def stream_response_body(response: httpx.Response) -> AsyncIterator[bytes]:
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    finally:
        await response.aclose()
