from __future__ import annotations

import uuid

from studio_contracts.tutor_schemas import TutorChatRequest


def test_tutor_chat_request_accepts_uuid_string_from_json() -> None:
    payload = {
        "session_id": "43d52088-0a5f-4bd1-9654-d90ac7bf332e",
        "message": "why does this fail?",
    }
    parsed = TutorChatRequest.model_validate(payload)
    assert parsed.session_id == uuid.UUID(payload["session_id"])
    assert parsed.message == payload["message"]
    assert parsed.history == []


def test_tutor_chat_request_accepts_history() -> None:
    payload = {
        "session_id": "43d52088-0a5f-4bd1-9654-d90ac7bf332e",
        "message": "and now?",
        "history": [
            {"role": "user", "content": "explain JOIN"},
            {"role": "assistant", "content": "JOIN combines rows."},
        ],
    }
    parsed = TutorChatRequest.model_validate(payload)
    assert len(parsed.history) == 2
    assert parsed.history[0].role == "user"
