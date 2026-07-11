from __future__ import annotations

import uuid

import pytest
from app.domain.check import GradingError, parse_attempt_id


def test_parse_attempt_id_accepts_uuid() -> None:
    attempt_id = uuid.uuid4()
    parsed = parse_attempt_id({"attempt_id": str(attempt_id)})
    assert parsed == attempt_id


def test_parse_attempt_id_rejects_missing_value() -> None:
    with pytest.raises(GradingError, match="attempt_id"):
        parse_attempt_id({})
