from __future__ import annotations

from app.domain.llm.content.json_mode import looks_like_unsupported_json_mode


def test_looks_like_unsupported_json_mode_detects_common_gateways() -> None:
    assert looks_like_unsupported_json_mode(ValueError("Unknown parameter: 'response_format'"))
    assert looks_like_unsupported_json_mode(ValueError("json_object is not supported"))
    assert looks_like_unsupported_json_mode(
        ValueError("Invalid request: Extra inputs are not permitted")
    )
    assert not looks_like_unsupported_json_mode(ValueError("rate limit exceeded"))
    assert not looks_like_unsupported_json_mode(ValueError("invalid API key"))
