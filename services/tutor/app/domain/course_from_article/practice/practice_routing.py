from __future__ import annotations

import re

_RUNTIME_VERSIONS: dict[str, str] = {
    "python": "3.12",
    "javascript": "18.15.0",
    "typescript": "5.0.3",
    "go": "1.16.2",
    "sql": "3.36.0",
    "sqlite3": "3.36.0",
    "bash": "5.2.0",
    "java": "15.0.2",
}

_RUNTIME_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("java", ("public class", "java.", "spring boot", "maven", "gradle", "jvm", "kotlin")),
    ("go", ("package main", "func main", "golang", "go mod")),
    ("typescript", ("typescript", "interface ", ": string", "npm run")),
    ("javascript", ("javascript", "node.js", "react", "const ", "npm ")),
    ("sql", ("select ", "create table", "postgresql", "sqlite", "join ")),
    ("bash", ("```bash", "```shell", "```sh", "\n$ ", " shell ", " terminal ")),
    ("python", ("def ", "import ", "python", "pip install", "pytest")),
)

_COMMAND_COURSE_TITLE = re.compile(
    r"(?i)(?:\bcli\b|command[- ]line|shell|terminal|devops|"
    r"инфраструктур|командн\w*\s+строк|терминал)"
)

_COMMAND_EXAMPLE_RE = re.compile(
    r"(?:"
    r"```(?:bash|shell|sh|zsh|console)\b|"
    r"^\s*\$\s+\S+|"
    r"\b[\w.-]+-cli\b|"
    r"\b[a-z][\w.-]*\s+(?:run|build|apply|create|install|start|deploy|init|set|get)\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
_ARTIFACT_MARKERS = (
    "config",
    "configuration",
    "manifest",
    "yaml",
    "yml",
    "toml",
    "конфигурац",
    "манифест",
    "команд",
    "скрипт",
)
_ARTIFACT_TASK_RE = re.compile(
    r"(?:"
    r"\b(?:file|config(?:uration)?|manifest|script|commands?)\b|"
    r"\b\w+file\b|"
    r"(?:файл|конфигурац\w*|манифест\w*|скрипт\w*|команд\w*)"
    r")",
    re.IGNORECASE,
)


def infer_course_runtime(
    *,
    title: str,
    corpus: str,
    fallback: str | None = "python",
) -> tuple[str, str]:
    blob = f"{title}\n{corpus[:20_000]}".casefold()
    scores: dict[str, int] = {name: 0 for name, _ in _RUNTIME_SIGNALS}
    for name, tokens in _RUNTIME_SIGNALS:
        scores[name] = sum(1 for token in tokens if token in blob)
    best = max(scores, key=lambda key: scores[key])
    runtime = (fallback or "python").strip().casefold() if scores[best] <= 0 else best
    version = _RUNTIME_VERSIONS.get(runtime, _RUNTIME_VERSIONS["python"])
    return runtime, version


def is_command_oriented_course(*, title: str, corpus: str) -> bool:
    blob = f"{title}\n{corpus[:20_000]}".casefold()
    command_hits = len(_COMMAND_EXAMPLE_RE.findall(blob))
    artifact_hits = sum(1 for marker in _ARTIFACT_MARKERS if marker in blob)
    if _COMMAND_COURSE_TITLE.search(title) and command_hits:
        return True
    if command_hits >= 2 and artifact_hits:
        return True
    return command_hits >= 3


def should_use_open_practice(
    *,
    title: str,
    corpus: str,
    domain: str,
    profile: str = "",
) -> bool:
    from app.domain.course_from_article.curriculum.outline.course_profile import course_family

    family = course_family(profile)
    if family in {"humanities", "language", "business", "science"}:
        return True
    return domain in {"language", "general"} and family != "technical"


def is_python_artifact_shim(*, template: str, content: str) -> bool:
    tpl = template.casefold()
    body = content.casefold()
    if "def " not in tpl or "return" not in tpl:
        return False
    if not _ARTIFACT_TASK_RE.search(f"{tpl}\n{body}"):
        return False
    return bool(re.search(r"return\s+(?:[rubf]*[\"']|[A-Za-z_]\w*)", tpl))
