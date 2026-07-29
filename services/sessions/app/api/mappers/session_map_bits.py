from __future__ import annotations

from typing import cast

from app.infra.models import Attempt, PhaseProgress
from studio_contracts.manifest import PhaseName
from studio_contracts.session_schemas import AttemptInfo, PhaseProgressInfo


def phase_progress(row: PhaseProgress) -> PhaseProgressInfo:
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
