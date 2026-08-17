_MIN_CODE_TEMPLATE_LENGTH = 20
_CODE_PLACEHOLDERS = {"...", "pass", "todo", "todo:", "notimplemented"}


def code_template_is_substantive(template: str) -> bool:
    source = template.strip()
    if len(source) < _MIN_CODE_TEMPLATE_LENGTH:
        return False
    for line in source.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith(("#", "//", "--", "/*", "*", "*/")):
            continue
        if candidate.casefold() not in _CODE_PLACEHOLDERS:
            return True
    return False
