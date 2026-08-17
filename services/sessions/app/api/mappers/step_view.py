from __future__ import annotations

from typing import cast

from app.api.mappers.step_view_meta import (
    _code_editor,
    _nav_target,
    _phase_transitions,
    _tutor_meta,
)
from app.infra.models import Session
from studio_contracts.api.session_schemas import StepContent
from studio_contracts.packs.manifest import PhaseName, adjacent_positions, get_step, read_policies

_CODE_EDITOR_KEYS = frozenset({"runtime", "runtime_version", "template", "setup"})
_HIDDEN_STEP_KEYS = frozenset(
    {"answer", "exemplar", "kind", "tests", "checks", "expected", "oracle"}
)


def build_step_view(learning_session: Session) -> StepContent:
    step = get_step(learning_session.manifest, learning_session.current_step_id)
    kind = step.get("kind")
    title = step.get("title")
    is_code = kind == "code"
    policies = read_policies(learning_session.manifest)
    content = {
        key: value
        for key, value in step.items()
        if key not in _HIDDEN_STEP_KEYS and (not is_code or key not in _CODE_EDITOR_KEYS)
    }
    editor = _code_editor(learning_session, step, policies) if is_code else None
    tutor = _tutor_meta(phase=cast(PhaseName, learning_session.current_phase), policies=policies)
    topic_id = learning_session.current_topic_id
    phase = cast(PhaseName, learning_session.current_phase)
    prev_pos, next_pos = adjacent_positions(
        learning_session.manifest,
        topic_id,
        phase,
        learning_session.current_step_id,
    )
    return StepContent(
        topic_id=topic_id,
        phase=phase,
        step_id=learning_session.current_step_id,
        kind=kind if isinstance(kind, str) else "unknown",
        title=title if isinstance(title, str) else "",
        content=content,
        editor=editor,
        tutor=tutor,
        transitions=_phase_transitions(learning_session.manifest, topic_id),
        prev_step=_nav_target(prev_pos),
        next_step=_nav_target(next_pos),
    )
