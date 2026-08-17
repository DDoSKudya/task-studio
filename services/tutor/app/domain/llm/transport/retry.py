from __future__ import annotations

import asyncio
import datetime as dt
import random
from collections.abc import Awaitable, Callable, Mapping
from email.utils import parsedate_to_datetime

import httpx

_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
_TRANSIENT_VALUE_MARKERS = (
    "empty llm content",
    "empty llm response",
    "empty response",
    "expected json object",
    "invalid json",
    "jsondecode",
    "runner process has terminated",
    "model is unloading",
)
_JSON_SHAPE_MARKERS = (
    "expected json object",
    "invalid json",
    "jsondecode",
    "empty llm content",
    "empty llm response",
    "empty response",
)
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
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, ValueError):
        detail = str(exc).casefold()
        return any(marker in detail for marker in _TRANSIENT_VALUE_MARKERS)
    return is_json_shape_error(exc)


def is_json_shape_error(exc: BaseException) -> bool:
    detail = str(getattr(exc, "detail", None) or exc).casefold()
    return any(marker in detail for marker in _JSON_SHAPE_MARKERS)


def is_retryable_json_failure(exc: BaseException) -> bool:
    return is_transient_llm_error(exc) or is_json_shape_error(exc)


def should_retry_json_error(exc: BaseException, *, attempt: int, attempts: int) -> bool:
    return is_json_shape_error(exc) and attempt < attempts - 1


async def retry_until_mapping(
    generate_raw: Callable[[], Awaitable[str]],
    parse_raw: Callable[[str], Awaitable[Mapping[str, object] | None]],
    *,
    retries: int = 2,
    base_delay_seconds: float = 0.4,
    max_delay_seconds: float = 4.0,
) -> dict[str, object]:
    last_raw = ""
    last_exc: BaseException | None = None
    attempts = max(0, retries) + 1
    for attempt in range(attempts):
        try:
            last_raw = await generate_raw()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if attempt + 1 >= attempts or not is_retryable_json_failure(exc):
                raise
            last_exc = exc
            delay = min(max_delay_seconds, base_delay_seconds * (2**attempt))
            await asyncio.sleep(delay)
            continue
        parsed = await parse_raw(last_raw)
        if parsed is not None:
            return dict(parsed)
        if attempt + 1 >= attempts:
            break
        delay = min(max_delay_seconds, base_delay_seconds * (2**attempt))
        await asyncio.sleep(delay)
    if last_exc is not None and not last_raw.strip():
        raise last_exc
    raise ValueError("expected JSON object")


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
