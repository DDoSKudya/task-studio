from __future__ import annotations

import re

# Версии по умолчанию — те же, что ставит scripts/install_piston_packages.py.
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
    ("python", ("def ", "import ", "python", "pip install", "pytest")),
)

_CLI_OPS_TITLE = re.compile(
    r"(?i)(docker|kubernetes|k8s|helm|terraform|devops|контейнер|container(?:s|ization)?)"
)

_CLI_OPS_MARKERS = (
    "dockerfile",
    "docker run",
    "docker build",
    "docker compose",
    "docker-compose",
    "kubectl",
    "образ контейнера",
    "docker hub",
    "docker image",
    "контейнер",
)


def infer_course_runtime(
    *,
    title: str,
    corpus: str,
    fallback: str | None = "python",
) -> tuple[str, str]:
    """Подбирает runtime по корпусу статьи, а не по дефолту клиента."""
    blob = f"{title}\n{corpus[:20_000]}".casefold()
    scores: dict[str, int] = {name: 0 for name, _ in _RUNTIME_SIGNALS}
    for name, tokens in _RUNTIME_SIGNALS:
        scores[name] = sum(1 for token in tokens if token in blob)
    best = max(scores, key=lambda key: scores[key])
    runtime = (fallback or "python").strip().casefold() if scores[best] <= 0 else best
    version = _RUNTIME_VERSIONS.get(runtime, _RUNTIME_VERSIONS["python"])
    return runtime, version


def is_cli_ops_course(*, title: str, corpus: str) -> bool:
    """
    DevOps / Docker / shell-first курсы: практика — команды, Dockerfile, конфиги,
    а не функции в Python.
    """
    blob = f"{title}\n{corpus[:20_000]}".casefold()
    marker_hits = sum(1 for marker in _CLI_OPS_MARKERS if marker in blob)
    title_ops = bool(_CLI_OPS_TITLE.search(title))
    if title_ops and marker_hits >= 2:
        return True
    if marker_hits >= 5:
        return True
    return "dockerfile" in blob and marker_hits >= 2


def should_use_open_practice(
    *,
    title: str,
    corpus: str,
    domain: str,
) -> bool:
    if domain in {"language", "general"}:
        return True
    return is_cli_ops_course(title=title, corpus=corpus)


def is_python_dockerfile_shim(*, template: str, content: str) -> bool:
    """LLM-антимодель: def create_dockerfile() -> str с heredoc Dockerfile внутри."""
    tpl = template.casefold()
    body = content.casefold()
    if "def " not in tpl:
        return False
    if "dockerfile" not in tpl and "dockerfile" not in body:
        return False
    if "from python:" in tpl or "from python:" in body:
        return True
    return "return" in tpl and ("from " in tpl or "workdir" in tpl)
