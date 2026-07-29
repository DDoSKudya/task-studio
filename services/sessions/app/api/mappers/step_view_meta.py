from __future__ import annotations

from app.infra.models import Session
from studio_contracts.editor_schemas import runtime_lsp
from studio_contracts.manifest import PackPolicies, PhaseName, SessionPosition, phase_step_ids
from studio_contracts.session_schemas import StepNavTarget
from studio_contracts.tutor_schemas import StepTutorInfo, tutor_allowed, tutor_mode_for_phase


def nav_target(position: SessionPosition | None) -> StepNavTarget | None:
    if position is None:
        return None
    return StepNavTarget(
        topic=position.topic_id,
        phase=position.phase,
        step=position.step_id,
    )


def phase_transitions(manifest: dict[str, object], topic_id: str) -> dict[str, str]:
    return {
        phase: steps[0]
        for phase in ("practice", "assess")
        if (steps := phase_step_ids(manifest, topic_id, phase))
    }


def tutor_meta(*, phase: PhaseName, policies: PackPolicies) -> StepTutorInfo | None:
    mode = tutor_mode_for_phase(phase)
    if mode is None:
        return None
    if not tutor_allowed(phase, pack_tutor_enabled=policies.tutor_enabled, user_enabled=True):
        return None
    return StepTutorInfo(enabled=True, mode=mode)


def code_editor(
    learning_session: Session,
    step: dict[str, object],
    policies: PackPolicies,
) -> dict[str, object]:
    runtime = step.get("runtime", "python")
    runtime_name = runtime if isinstance(runtime, str) else "python"
    is_assess = learning_session.current_phase == "assess"
    autocomplete = policies.assess_autocomplete if is_assess else True
    return {
        "runtime": runtime_name,
        "runtime_version": step.get("runtime_version", "3.12"),
        "template": step.get("template", ""),
        "autocomplete": autocomplete,
        "lsp": runtime_lsp(runtime_name),
    }


                                                               
_nav_target = nav_target
_phase_transitions = phase_transitions
_tutor_meta = tutor_meta
_code_editor = code_editor
