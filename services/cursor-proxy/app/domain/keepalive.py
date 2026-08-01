from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


async def wait_ready_with_keepalive[T](
    task: asyncio.Task[T],
    *,
    poll_interval: float = 8.0,
) -> AsyncIterator[bytes]:
    while True:
        if task.done():
            return
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=poll_interval)
            return
        except TimeoutError:
            yield b": keepalive\n\n"
