from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.config import GradingSettings


def _settings() -> GradingSettings:
    return GradingSettings(
        piston_url="http://piston",
        piston_timeout_seconds=1.0,
        rabbitmq_url="",
        grading_jobs_queue="g",
        lab_jobs_queue="l",
        catalog_service_url="http://catalog",
        sessions_service_url="http://sessions",
        auth_service_url="http://auth",
        tutor_service_url="http://tutor",
        media_service_url="http://media",
        packs_root="/tmp",
        llm_grade_enabled=False,
        llm_grade_min_confidence=0.5,
        secrets_master_key=None,
    )


@pytest.mark.asyncio
async def test_complete_lab_retries_sessions_before_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.lab import service as lab_service

    attempt_id = uuid.uuid4()
    session = AsyncMock()
    client = AsyncMock()
    fail = httpx.ConnectError("down")
    ok = MagicMock()
    ok.status_code = 204
    ok.raise_for_status = MagicMock()
    client.post = AsyncMock(side_effect=[fail, fail, ok])

    persist = AsyncMock()
    monkeypatch.setattr(lab_service, "get_lab_result", AsyncMock(return_value=None))
    monkeypatch.setattr(lab_service, "persist_lab_result", persist)
    monkeypatch.setattr(lab_service, "system_token_headers", lambda: {})
    monkeypatch.setattr(lab_service.asyncio, "sleep", AsyncMock())

    await lab_service.complete_lab_job(
        session,
        _settings(),
        client,
        attempt_id=attempt_id,
        passed=True,
        score=1.0,
        feedback="ok",
        details={"status": "completed"},
        duration_ms=12,
    )

    assert client.post.await_count == 3
    persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_lab_does_not_persist_when_callback_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.lab import service as lab_service

    attempt_id = uuid.uuid4()
    session = AsyncMock()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=httpx.ConnectError("down"))

    persist = AsyncMock()
    monkeypatch.setattr(lab_service, "get_lab_result", AsyncMock(return_value=None))
    monkeypatch.setattr(lab_service, "persist_lab_result", persist)
    monkeypatch.setattr(lab_service, "system_token_headers", lambda: {})
    monkeypatch.setattr(lab_service.asyncio, "sleep", AsyncMock())

    with pytest.raises(httpx.ConnectError):
        await lab_service.complete_lab_job(
            session,
            _settings(),
            client,
            attempt_id=attempt_id,
            passed=True,
            score=1.0,
            feedback="ok",
            details={"status": "completed"},
            duration_ms=12,
        )

    assert client.post.await_count == 3
    persist.assert_not_awaited()
