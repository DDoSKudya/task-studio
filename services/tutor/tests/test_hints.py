from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_load_fallback_rules_has_code_hints() -> None:
    hints = load_service_module("app.domain.hints")
    rules = hints.load_fallback_rules()
    assert "code" in rules
    assert rules["code"]


def test_hints_for_kind_returns_strings() -> None:
    hints = load_service_module("app.domain.hints")
    result = hints.hints_for_kind("quiz")
    assert result
    assert all(isinstance(hint, str) for hint in result)


def test_hints_for_unknown_kind_falls_back() -> None:
    hints = load_service_module("app.domain.hints")
    result = hints.hints_for_kind("unknown-kind")
    assert result
