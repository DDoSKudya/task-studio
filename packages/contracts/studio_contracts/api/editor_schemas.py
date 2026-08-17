from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_contracts.packs.manifest import PhaseName

EditorMode = Literal["full", "syntax_only"]

_RUNTIME_LSP: dict[str, str] = {
    "python": "pyright",
    "javascript": "typescript",
    "go": "gopls",
    "sql": "sqls",
}


class EditorLanguageSettings(BaseModel):
    model_config = ConfigDict(strict=True)

    enabled: bool = True


class EditorSettings(BaseModel):
    model_config = ConfigDict(strict=True)

    autocomplete: bool = True
    mode: EditorMode = "full"
    languages: dict[str, EditorLanguageSettings] = Field(default_factory=dict)


def parse_editor_settings(user_settings: dict[str, object]) -> EditorSettings:
    raw = user_settings.get("editor")
    if isinstance(raw, dict):
        return EditorSettings.model_validate(raw)
    return EditorSettings()


def runtime_lsp(runtime: str) -> str | None:
    return _RUNTIME_LSP.get(runtime)


def lsp_enabled(
    editor_settings: EditorSettings,
    *,
    phase: PhaseName,
    pack_autocomplete: bool,
    runtime: str,
) -> bool:
    if editor_settings.mode == "syntax_only":
        return False
    if not editor_settings.autocomplete:
        return False
    if phase == "assess" and not pack_autocomplete:
        return False
    language = editor_settings.languages.get(runtime)
    if language is not None and not language.enabled:
        return False
    return runtime_lsp(runtime) is not None
