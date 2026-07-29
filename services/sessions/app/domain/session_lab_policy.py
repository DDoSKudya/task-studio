from __future__ import annotations


def lab_should_sync_llm(step: dict[str, object]) -> bool:
    checker = step.get("checker")
    if isinstance(checker, str) and checker.strip().lower() == "llm":
        return True
    lab = step.get("lab")
    if not isinstance(lab, dict):
        lab = step.get("docker")
    if not isinstance(lab, dict):
        return True
    image = lab.get("image")
    return not isinstance(image, str) or not image.strip()
