from __future__ import annotations


def lab_should_sync_llm(step: dict[str, object]) -> bool:
    checker = step.get("checker")
    if isinstance(checker, str) and checker.strip().lower() == "llm":
        return True

    compose = step.get("compose_file")
    if isinstance(compose, str) and compose.strip():
        return False

    for key in ("lab", "docker"):
        block = step.get(key)
        if not isinstance(block, dict):
            continue
        nested_compose = block.get("compose_file")
        if isinstance(nested_compose, str) and nested_compose.strip():
            return False
        image = block.get("image")
        if isinstance(image, str) and image.strip():
            return False

    return True
