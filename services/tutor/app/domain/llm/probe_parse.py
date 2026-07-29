from __future__ import annotations


def model_aliases(name: str) -> set[str]:
    cleaned = name.strip()
    if not cleaned:
        return set()
    aliases = {cleaned}
    if cleaned.endswith(":latest"):
        aliases.add(cleaned[: -len(":latest")])
    else:
        aliases.add(f"{cleaned}:latest")
    return aliases


def model_is_available(wanted: str | None, installed: list[str]) -> bool:
    if not wanted or not wanted.strip():
        return True
    wanted_aliases = model_aliases(wanted)
    return any(model_aliases(item) & wanted_aliases for item in installed)


def resolve_installed_model(wanted: str | None, installed: list[str]) -> str | None:
                                                                               
    if not installed:
        return None
    if not wanted or not wanted.strip():
        return installed[0]
    wanted_aliases = model_aliases(wanted)
    for item in installed:
        if model_aliases(item) & wanted_aliases:
            return item
    return None


def parse_openai_model_ids(payload: object) -> list[str]:
    models: list[str] = []
    if not isinstance(payload, dict):
        return models
    data = payload.get("data")
    if not isinstance(data, list):
        return models
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            models.append(item["id"])
    return sorted(set(models), key=str.casefold)


def parse_ollama_model_names(payload: object) -> list[str]:
    models: list[str] = []
    rows = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return models
    for item in rows:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if isinstance(name, str) and name.strip():
            models.append(name.strip())
    return sorted(set(models), key=str.casefold)
