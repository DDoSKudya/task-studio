from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from studio_contracts.grading_schemas import GradingCheckResponse
from studio_contracts.manifest import SessionPosition


@pytest.mark.asyncio
async def test_apply_grading_result_clears_flags_after_failed_regrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain import session_grade_apply as apply_mod

    progress = SimpleNamespace(
        practice_completed=True, assess_completed=False, assess_best_score=None
    )
    learning = MagicMock()
    learning.id = uuid.uuid4()
    learning.current_topic_id = "t1"
    learning.current_phase = "practice"
    learning.status = "completed"

    attempt = MagicMock()
    attempt.topic_id = "t1"
    attempt.phase = "practice"
    attempt.step_id = "s1"

    async def fake_progress(*_a: object, **_k: object) -> SimpleNamespace:
        return progress

    async def fake_practice(*_a: object, **_k: object) -> bool:
        return False

    async def fake_session_completed(*_a: object, **_k: object) -> bool:
        return False

    monkeypatch.setattr(apply_mod, "_get_or_create_progress", fake_progress)
    monkeypatch.setattr(apply_mod, "_topic_practice_passed", fake_practice)
    monkeypatch.setattr(apply_mod, "_session_completed", fake_session_completed)

    ok = await apply_mod.apply_grading_result(
        MagicMock(),
        learning,
        GradingCheckResponse(passed=False, score=0.0),
        attempt=attempt,
    )
    assert ok is False
    assert progress.practice_completed is False
    assert learning.status == "active"


@pytest.mark.asyncio
async def test_complete_attempt_ignores_abandoned_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain import session_attempts as attempts_mod

    attempt = MagicMock()
    attempt.id = uuid.uuid4()
    attempt.session_id = uuid.uuid4()
    attempt.result = {"passed": True}

    learning = MagicMock()
    learning.id = attempt.session_id
    learning.status = "abandoned"

    class _Result:
        def scalar_one_or_none(self) -> MagicMock:
            return attempt

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_Result())
    session.get = AsyncMock(return_value=learning)

    apply_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(attempts_mod, "apply_grading_result", apply_mock)

    outcome = await attempts_mod.complete_attempt(
        session,
        attempt.id,
        passed=False,
        score=0.0,
        feedback=None,
        details={},
    )
    assert outcome.phase_completed is False
    apply_mock.assert_not_awaited()
    assert attempt.result == {"passed": True}
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_gate_leave_rejects_ungradable_without_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain import session_gate_leave as gate_mod
    from app.domain.session_errors import SessionError

    learning = MagicMock()
    learning.id = uuid.uuid4()
    learning.current_topic_id = "t1"
    learning.current_phase = "practice"
    learning.current_step_id = "quiz-1"
    learning.manifest = {
        "topics": [
            {
                "id": "t1",
                "phases": {
                    "practice": {
                        "steps": [
                            {"id": "quiz-1", "kind": "quiz"},
                            {"id": "quiz-2", "kind": "quiz"},
                        ]
                    }
                },
            }
        ]
    }

    async def fake_passed(*_a: object, **_k: object) -> set[str]:
        return set()

    monkeypatch.setattr(gate_mod, "passed_step_ids", fake_passed)
    monkeypatch.setattr(
        gate_mod,
        "position_index",
        lambda _manifest, pos: 0 if pos.step_id == "quiz-1" else 1,
    )
    monkeypatch.setattr(
        gate_mod,
        "get_step",
        lambda _m, step_id: {"id": step_id, "kind": "quiz"},
    )

    with pytest.raises(SessionError) as exc:
        await gate_mod.ensure_can_leave_gated_step(
            MagicMock(),
            learning,
            target=SessionPosition(topic_id="t1", phase="practice", step_id="quiz-2"),
        )
    assert exc.value.status_code == 403


def test_submit_event_pending_lab_is_queued() -> None:
    from app.domain.analytics_events import submit_event

    learning = MagicMock()
    learning.id = uuid.uuid4()
    learning.user_id = uuid.uuid4()
    learning.pack_version_id = uuid.uuid4()
    learning.pack_title = "Pack"
    learning.current_topic_id = "t1"
    learning.current_phase = "practice"
    learning.current_step_id = "lab-1"
    learning.manifest = {
        "steps": {"lab-1": {"id": "lab-1", "kind": "lab"}},
        "topics": [
            {
                "id": "t1",
                "phases": {
                    "practice": {"steps": ["lab-1"]},
                },
            }
        ],
    }
    attempt = MagicMock()
    attempt.id = uuid.uuid4()
    attempt.topic_id = "t1"
    attempt.phase = "practice"
    attempt.step_id = "lab-1"
    attempt.attempt_number = 1
    grading = GradingCheckResponse(passed=False, score=0.0, details={"status": "pending"})
    event = submit_event(learning, attempt, grading, outcome_status="pending")
    assert event.event_type == "lab_queued"
    assert event.payload.get("status") == "pending"
    assert "passed" not in event.payload
