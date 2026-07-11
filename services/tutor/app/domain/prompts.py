from __future__ import annotations

from pathlib import Path

from studio_contracts.manifest import PhaseName

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def system_prompt_for_phase(phase: PhaseName, *, step_kind: str, step_title: str) -> str:
    template = load_prompt("study_hint" if phase == "study" else "practice")
    return template.replace("{{step_kind}}", step_kind).replace("{{step_title}}", step_title)
