from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.infra.models import Attempt, Session
from studio_contracts.api.grading_schemas import GradingCheckResponse


class SessionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class SubmitOutcome:
    attempt: Attempt
    grading: GradingCheckResponse
    phase_completed: bool
    status: Literal["completed", "pending"] = "completed"
    learning_session: Session | None = None
