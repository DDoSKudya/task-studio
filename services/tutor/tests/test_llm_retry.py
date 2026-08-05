from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

import httpx
import pytest

_UTC = dt.UTC if hasattr(dt, "UTC") else dt.timezone.utc  # noqa: UP017


def _load_retry_module():
    module_path = Path(__file__).resolve().parents[1] / "app" / "domain" / "llm" / "retry.py"
    spec = importlib.util.spec_from_file_location("tutor_llm_retry_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _http_status_error(response: httpx.Response) -> Exception:
    try:
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return exc
    raise AssertionError("expected HTTP status error")


def test_retry_delay_prefers_retry_after_ms() -> None:
    retry = _load_retry_module()
    response = httpx.Response(
        429,
        headers={"retry-after-ms": "1500"},
        request=httpx.Request("POST", "http://x/v1/chat/completions"),
    )
    exc = _http_status_error(response)
    delay = retry.retry_delay_seconds(
        exc,
        attempt=0,
        base_delay_seconds=1.0,
        max_delay_seconds=20.0,
    )
    assert delay == pytest.approx(1.5)


def test_retry_delay_prefers_retry_after_seconds() -> None:
    retry = _load_retry_module()
    response = httpx.Response(
        429,
        headers={"retry-after": "3"},
        request=httpx.Request("POST", "http://x/v1/chat/completions"),
    )
    exc = _http_status_error(response)
    delay = retry.retry_delay_seconds(
        exc,
        attempt=1,
        base_delay_seconds=1.0,
        max_delay_seconds=20.0,
    )
    assert delay == pytest.approx(3.0)


def test_retry_delay_supports_retry_after_http_date() -> None:
    retry = _load_retry_module()
    future = dt.datetime.now(_UTC) + dt.timedelta(seconds=4)
    response = httpx.Response(
        429,
        headers={"retry-after": future.strftime("%a, %d %b %Y %H:%M:%S GMT")},
        request=httpx.Request("POST", "http://x/v1/chat/completions"),
    )
    exc = _http_status_error(response)
    delay = retry.retry_delay_seconds(
        exc,
        attempt=2,
        base_delay_seconds=1.0,
        max_delay_seconds=20.0,
    )
    assert 0.0 <= delay <= 4.5


def test_retry_delay_uses_full_jitter_window(monkeypatch: pytest.MonkeyPatch) -> None:
    retry = _load_retry_module()
    monkeypatch.setattr(retry.random, "uniform", lambda low, high: high)
    delay = retry.retry_delay_seconds(
        httpx.ReadTimeout("slow"),
        attempt=2,
        base_delay_seconds=1.0,
        max_delay_seconds=20.0,
    )
    assert delay == pytest.approx(4.0)


@pytest.mark.asyncio
async def test_with_llm_retry_uses_jitter_window(monkeypatch: pytest.MonkeyPatch) -> None:
    retry = _load_retry_module()
    sleeps: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(retry.asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(retry.random, "uniform", lambda low, high: high)

    attempts = 0

    async def _operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            response = httpx.Response(
                503,
                request=httpx.Request("POST", "http://x/v1/chat/completions"),
            )
            raise _http_status_error(response)
        return "ok"

    result = await retry.with_llm_retry(
        _operation,
        retries=1,
        base_delay_seconds=1.0,
        max_delay_seconds=20.0,
    )
    assert result == "ok"
    assert sleeps == [1.0]
