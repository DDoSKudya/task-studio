from __future__ import annotations

from typing import cast

from app.infra.models import Attempt, PhaseProgress, Session
from studio_contracts.manifest import PhaseName, get_step, phase_step_ids, read_policies
from studio_contracts.session_schemas import (
    AttemptInfo,
    PhaseProgressInfo,
    SessionState,
    SessionStatus,
    SessionSummary,
    StepContent,
)

_CODE_EDITOR_KEYS = frozenset({"runtime", "runtime_version", "template"})


def session_summary(learning_session: Session) -> SessionSummary:
    return SessionSummary(
        id=learning_session.id,
        pack_version_id=learning_session.pack_version_id,
        pack_title=learning_session.pack_title,
        status=cast(SessionStatus, learning_session.status),
        current_topic_id=learning_session.current_topic_id,
        current_phase=cast(PhaseName, learning_session.current_phase),
        current_step_id=learning_session.current_step_id,
        started_at=learning_session.started_at,
        updated_at=learning_session.updated_at,
    )


def session_state(learning_session: Session, progress_rows: list[PhaseProgress]) -> SessionState:
    policies = read_policies(learning_session.manifest)
    return SessionState(
        id=learning_session.id,
        pack_version_id=learning_session.pack_version_id,
        pack_title=learning_session.pack_title,
        status=cast(SessionStatus, learning_session.status),
        current_topic_id=learning_session.current_topic_id,
        current_phase=cast(PhaseName, learning_session.current_phase),
        current_step_id=learning_session.current_step_id,
        policies=policies,
        phase_progress=[_phase_progress(row) for row in progress_rows],
        started_at=learning_session.started_at,
        updated_at=learning_session.updated_at,
    )


def build_step_view(learning_session: Session) -> StepContent:
    step = get_step(learning_session.manifest, learning_session.current_step_id)
    kind = step.get("kind")
    title = step.get("title")
    is_code = kind == "code"
    content = {
        key: value
        for key, value in step.items()
        if key != "kind" and (not is_code or key not in _CODE_EDITOR_KEYS)
    }
    editor = _code_editor(learning_session, step) if is_code else None
    topic_id = learning_session.current_topic_id
    return StepContent(
        topic_id=topic_id,
        phase=cast(PhaseName, learning_session.current_phase),
        step_id=learning_session.current_step_id,
        kind=kind if isinstance(kind, str) else "unknown",
        title=title if isinstance(title, str) else "",
        content=content,
        editor=editor,
        transitions=_phase_transitions(learning_session.manifest, topic_id),
    )


def _phase_transitions(manifest: dict[str, object], topic_id: str) -> dict[str, str]:
    return {
        phase: steps[0]
        for phase in ("practice", "assess")
        if (steps := phase_step_ids(manifest, topic_id, phase))
    }


def _code_editor(learning_session: Session, step: dict[str, object]) -> dict[str, object]:
    autocomplete = True
    if learning_session.current_phase == "assess":
        autocomplete = read_policies(learning_session.manifest).assess_autocomplete
    return {
        "runtime": step.get("runtime", "python"),
        "runtime_version": step.get("runtime_version", "3.12"),
        "template": step.get("template", ""),
        "autocomplete": autocomplete,
    }


def _phase_progress(row: PhaseProgress) -> PhaseProgressInfo:
    best = row.assess_best_score
    return PhaseProgressInfo(
        topic_id=row.topic_id,
        study_completed=row.study_completed,
        study_skipped=row.study_skipped,
        practice_completed=row.practice_completed,
        assess_completed=row.assess_completed,
        assess_best_score=float(best) if best is not None else None,
    )


def attempt_info(attempt: Attempt) -> AttemptInfo:
    return AttemptInfo(
        id=attempt.id,
        topic_id=attempt.topic_id,
        phase=cast(PhaseName, attempt.phase),
        step_id=attempt.step_id,
        attempt_number=attempt.attempt_number,
        submission=attempt.submission,
        result=attempt.result,
        created_at=attempt.created_at,
    )
