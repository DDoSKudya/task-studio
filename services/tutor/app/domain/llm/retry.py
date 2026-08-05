from __future__ import annotations

import asyncio
import datetime as dt
import random
from collections.abc import Awaitable, Callable
from email.utils import parsedate_to_datetime

import httpx

_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
_UTC = dt.UTC if hasattr(dt, "UTC") else dt.timezone.utc  # noqa: UP017
_TIMEOUT_TYPES = tuple(
    exc_type
    for exc_type in (
        getattr(httpx, "TimeoutException", None),
        getattr(httpx, "Timeout", None),
        getattr(httpx, "ReadTimeout", None),
        getattr(httpx, "WriteTimeout", None),
        getattr(httpx, "ConnectTimeout", None),
        getattr(httpx, "PoolTimeout", None),
    )
    if isinstance(exc_type, type)
)


def is_transient_llm_error(exc: BaseException) -> bool:
    if _TIMEOUT_TYPES and isinstance(exc, _TIMEOUT_TYPES):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_STATUS
    if isinstance(exc, httpx.HTTPError):
        response = getattr(exc, "response", None)
        if response is None:
            return True
        return response.status_code in _TRANSIENT_STATUS
    return bool(isinstance(exc, httpx.TransportError))


def _retry_after_seconds(response: httpx.Response) -> float | None:
    retry_after_ms = response.headers.get("retry-after-ms")
    if retry_after_ms:
        try:
            return max(0.0, float(retry_after_ms) / 1000.0)
        except ValueError:
            pass

    retry_after = response.headers.get("retry-after")
    if not retry_after:
        return None
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(retry_after)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=_UTC)
    delay = (retry_at - dt.datetime.now(_UTC)).total_seconds()
    return max(0.0, delay)


def retry_delay_seconds(
    exc: BaseException,
    *,
    attempt: int,
    base_delay_seconds: float,
    max_delay_seconds: float,
) -> float:
    response = getattr(exc, "response", None)
    if isinstance(response, httpx.Response):
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            return retry_after
    window = min(max_delay_seconds, base_delay_seconds * (2**attempt))
    return random.uniform(0.0, window)


async def with_llm_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int,
    base_delay_seconds: float = 3.0,
    max_delay_seconds: float = 180.0,
) -> T:
    attempt = 0
    while True:
        try:
            return await operation()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            if attempt >= retries or not is_transient_llm_error(exc):
                raise
            delay = retry_delay_seconds(
                exc,
                attempt=attempt,
                base_delay_seconds=base_delay_seconds,
                max_delay_seconds=max_delay_seconds,
            )
            await asyncio.sleep(delay)
            attempt += 1
