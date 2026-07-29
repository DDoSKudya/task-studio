from __future__ import annotations

import uuid
from types import ModuleType
from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_list_passed_step_ids_returns_sorted_distinct(
    sessions_domain: ModuleType,
) -> None:
    class _Result:
        def scalars(self):
            return iter(["step-b", "step-a"])

    async def fake_execute(_statement: object):
        return _Result()

    session = MagicMock()
    session.execute = fake_execute

    out = await sessions_domain.list_passed_step_ids(session, uuid.uuid4())
    assert out == ["step-a", "step-b"]
