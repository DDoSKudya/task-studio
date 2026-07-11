from __future__ import annotations

from studio_contracts.tutor_schemas import (
    parse_tutor_settings,
    tutor_allowed,
    tutor_mode_for_phase,
)


def test_parse_tutor_settings_defaults() -> None:
    settings = parse_tutor_settings({})
    assert settings.enabled is True
    assert settings.daily_limit == 0
    assert settings.provider_url is None


def test_parse_tutor_settings_from_blob() -> None:
    settings = parse_tutor_settings(
        {
            "tutor": {
                "enabled": False,
                "provider_url": "https://api.openai.com/v1",
                "daily_limit": 50,
                "model": "gpt-4o-mini",
            }
        }
    )
    assert settings.enabled is False
    assert settings.provider_url == "https://api.openai.com/v1"
    assert settings.daily_limit == 50
    assert settings.model == "gpt-4o-mini"


def test_tutor_forbidden_in_assess() -> None:
    assert (
        tutor_allowed(
            "assess",
            pack_tutor_enabled=True,
            user_enabled=True,
        )
        is False
    )


def test_tutor_allowed_in_practice() -> None:
    assert (
        tutor_allowed(
            "practice",
            pack_tutor_enabled=True,
            user_enabled=True,
        )
        is True
    )


def test_tutor_disabled_when_pack_blocks() -> None:
    assert (
        tutor_allowed(
            "practice",
            pack_tutor_enabled=False,
            user_enabled=True,
        )
        is False
    )


def test_tutor_mode_for_phase() -> None:
    assert tutor_mode_for_phase("study") == "hint"
    assert tutor_mode_for_phase("practice") == "chat"
    assert tutor_mode_for_phase("assess") is None
