from __future__ import annotations

from studio_contracts.editor_schemas import (
    EditorSettings,
    lsp_enabled,
    parse_editor_settings,
    runtime_lsp,
)


def test_runtime_lsp_maps_python() -> None:
    assert runtime_lsp("python") == "pyright"
    assert runtime_lsp("unknown") is None


def test_parse_editor_settings_defaults() -> None:
    settings = parse_editor_settings({})
    assert settings.autocomplete is True
    assert settings.mode == "full"


def test_parse_editor_settings_from_blob() -> None:
    settings = parse_editor_settings(
        {
            "editor": {
                "autocomplete": False,
                "mode": "syntax_only",
                "languages": {"python": {"enabled": False}},
            }
        }
    )
    assert settings.autocomplete is False
    assert settings.mode == "syntax_only"
    assert settings.languages["python"].enabled is False


def test_lsp_disabled_in_assess_when_pack_blocks() -> None:
    settings = EditorSettings()
    assert (
        lsp_enabled(
            settings,
            phase="assess",
            pack_autocomplete=False,
            runtime="python",
        )
        is False
    )


def test_lsp_enabled_in_practice() -> None:
    settings = EditorSettings()
    assert (
        lsp_enabled(
            settings,
            phase="practice",
            pack_autocomplete=False,
            runtime="python",
        )
        is True
    )
