from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.domain.cursor.client import (
    CursorApiError,
    _result_text_from_payload,
    _run_status,
    wait_for_run_result,
)


def test_run_status_reads_nested_payload() -> None:
    assert _run_status({"status": "running"}) == "RUNNING"
    assert _run_status({"run": {"status": "FINISHED"}}) == "FINISHED"
    assert _run_status({}) == ""


def test_result_text_from_payload() -> None:
    assert _result_text_from_payload({"result": "  hello  "}) == "hello"
    assert _result_text_from_payload({"run": {"text": "ok"}}) == "ok"
    assert _result_text_from_payload({"status": "FINISHED"}) is None


@pytest.mark.asyncio
async def test_wait_for_run_result_polls_until_finished() -> None:
    payloads = [
        {"status": "CREATING"},
        {"status": "RUNNING"},
        {"status": "FINISHED", "result": "SELECT * FROM cadets;"},
    ]

    async def fake_get_run(*_args, **_kwargs):
        return payloads.pop(0)

    with (
        patch("app.domain.cursor.run_poll.get_run", side_effect=fake_get_run),
        patch("app.domain.cursor.run_poll.asyncio.sleep", new_callable=AsyncMock),
    ):
        text = await wait_for_run_result(
            AsyncMock(),
            api_base="https://api.cursor.com",
            api_key="key",
            agent_id="bc-1",
            run_id="run-1",
            request_timeout=30.0,
            poll_interval=0.01,
        )
    assert text == "SELECT * FROM cadets;"


@pytest.mark.asyncio
async def test_wait_for_run_result_raises_on_error_status() -> None:
    async def fake_get_run(*_args, **_kwargs):
        return {"status": "ERROR"}

    with (
        patch("app.domain.cursor.run_poll.get_run", side_effect=fake_get_run),
        patch("app.domain.cursor.run_poll.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(CursorApiError) as exc,
    ):
        await wait_for_run_result(
            AsyncMock(),
            api_base="https://api.cursor.com",
            api_key="key",
            agent_id="bc-1",
            run_id="run-1",
            request_timeout=30.0,
            poll_interval=0.01,
        )
    assert exc.value.status_code == 502
    assert "ERROR" in exc.value.detail
