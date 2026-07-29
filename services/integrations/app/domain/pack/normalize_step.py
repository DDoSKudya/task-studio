from __future__ import annotations


def nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def coerce_adapter_step(raw: dict[str, object], inferred_phase: str | None) -> dict[str, object]:
    reserved = {"id", "kind", "title", "phase", "fidelity", "payload"}
    payload_raw = raw.get("payload")
    if isinstance(payload_raw, dict):
        payload = dict(payload_raw)
    else:
        payload = {key: value for key, value in raw.items() if key not in reserved}

    if not nonempty_str(payload.get("instructions")):
        for alias in ("body_html", "body_md", "content", "prompt_md", "theory_md"):
            candidate = payload.get(alias)
            if nonempty_str(candidate):
                payload["instructions"] = candidate
                break
            top = raw.get(alias)
            if nonempty_str(top):
                payload["instructions"] = top
                break
    if "question" not in payload and nonempty_str(raw.get("prompt_md")):
        payload["question"] = raw["prompt_md"]
    if "template" not in payload and nonempty_str(raw.get("starter_code")):
        payload["template"] = raw["starter_code"]

    phase_raw = raw.get("phase")
    if isinstance(phase_raw, str) and phase_raw in {"study", "practice", "assess"}:
        phase: str = phase_raw
    elif isinstance(inferred_phase, str) and inferred_phase in {"study", "practice", "assess"}:
        phase = inferred_phase
    else:
        phase = "study"

    fidelity_raw = raw.get("fidelity")
    fidelity = fidelity_raw if fidelity_raw in {"full", "partial"} else "full"

    kind_raw = raw.get("kind")
    kind = kind_raw if kind_raw in {"theory", "video", "quiz", "code", "lab", "task"} else "theory"

    step_id = raw.get("id")
    title = raw.get("title")
    return {
        "id": str(step_id) if step_id is not None else "step",
        "kind": kind,
        "title": str(title) if title is not None and str(title).strip() else "Step",
        "phase": phase,
        "fidelity": fidelity,
        "payload": payload,
    }
