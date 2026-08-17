from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvalArticle:
    title: str
    body: str


def _md(title: str, sections: tuple[tuple[str, str], ...]) -> EvalArticle:
    parts = [f"# {title}\n"]
    for heading, prose in sections:
        parts.append(f"## {heading}\n{prose.strip()}\n")
    return EvalArticle(title=title, body="\n".join(parts).strip())


EVAL_ARTICLES: tuple[EvalArticle, ...] = (
    _md(
        "FastAPI intro",
        (
            (
                "Minimal app",
                "FastAPI builds JSON APIs with type hints. "
                "Create app = FastAPI() then decorate a function with @app.get.",
            ),
            (
                "Path operations",
                "A path operation is a function bound to HTTP method and path. "
                "Return a dict and FastAPI serializes JSON.",
            ),
        ),
    ),
    _md(
        "APIRouter packages",
        (
            (
                "Group routes",
                "APIRouter groups related HTTP routes in a package so imports stay tidy.",
            ),
            (
                "Avoid cycles",
                "Keep router imports acyclic so packages load without circular graphs.",
            ),
        ),
    ),
    _md(
        "pathlib paths",
        (
            (
                "Path object",
                "Path wraps filesystem paths. Use / to join parts instead of os.path.join.",
            ),
            ("Name and stem", ".name is the final component; .stem drops the suffix."),
        ),
    ),
    _md(
        "asyncio tasks",
        (
            (
                "Event loop",
                "asyncio runs coroutines on one event loop. await yields control while I/O waits.",
            ),
            (
                "Gather",
                "asyncio.gather runs several coroutines concurrently and returns their results.",
            ),
        ),
    ),
    _md(
        "pytest fixtures",
        (
            (
                "Arrange with fixture",
                "A pytest fixture prepares data for tests. Yield for teardown after the test.",
            ),
            (
                "Scope",
                "function scope rebuilds per test; module scope shares one object in the file.",
            ),
        ),
    ),
    _md(
        "type hints",
        (
            (
                "Annotations",
                "Type hints document parameters and returns. "
                "They do not enforce types at runtime by themselves.",
            ),
            (
                "Optional",
                "T | None means the value may be missing. Check with is None before use.",
            ),
        ),
    ),
    _md(
        "Docker layers",
        (
            (
                "Cache deps",
                "Copy requirements before application code so dependency layers stay cached.",
            ),
            (
                "Slim image",
                "Use a slim base and a non-root user. Do not copy .env into the image.",
            ),
        ),
    ),
    _md(
        "Git commits",
        (
            (
                "Conventional header",
                "Commits use type(scope): description in English imperative mood.",
            ),
            (
                "Atomic change",
                "One logical change per commit so history stays bisectable.",
            ),
        ),
    ),
    _md(
        "SQL joins",
        (
            (
                "INNER JOIN",
                "INNER JOIN keeps rows that match on the join key in both tables.",
            ),
            (
                "LEFT JOIN trap",
                "A WHERE on the right table turns LEFT JOIN into INNER JOIN. "
                "Put that filter in ON.",
            ),
        ),
    ),
    _md(
        "Redis TTL",
        (
            (
                "Expire keys",
                "Cache keys need TTL so memory does not grow forever. "
                "INCR plus EXPIRE must be atomic.",
            ),
            (
                "SCAN not KEYS",
                "KEYS blocks the server. Use SCAN to iterate keys in production.",
            ),
        ),
    ),
    _md(
        "Vue refs",
        (
            (
                "ref and reactive",
                "ref wraps a primitive; reactive wraps an object. Template unwraps refs.",
            ),
            (
                "watch",
                "watch runs when a source changes. "
                "Prefer watchEffect only for simple derived work.",
            ),
        ),
    ),
    _md(
        "httpx async",
        (
            (
                "AsyncClient",
                "Use httpx.AsyncClient inside async def. Never call requests in the event loop.",
            ),
            (
                "Timeouts",
                "Set timeout on every call. A hanging peer should not freeze the tutor service.",
            ),
        ),
    ),
    _md(
        "Pydantic models",
        (
            (
                "BaseModel",
                "Pydantic validates input at the API boundary. Reject unknown types early.",
            ),
            (
                "model_dump",
                "model_dump(mode='json') serializes for JSON. exclude_unset helps PATCH.",
            ),
        ),
    ),
    _md(
        "Python logging",
        (
            (
                "Logger per module",
                "logging.getLogger(__name__) keeps logger names stable across packages.",
            ),
            ("No secrets", "Do not log tokens or API keys. Prefer structured extra fields."),
        ),
    ),
    _md(
        "Dataclasses",
        (
            (
                "Frozen records",
                "frozen=True makes a hashable record for dict keys when fields are immutable.",
            ),
            ("slots", "slots=True cuts per-instance size. Use for hot domain objects."),
        ),
    ),
    _md(
        "Context managers",
        (
            (
                "with blocks",
                "with opens a resource and guarantees close via __exit__, even on errors.",
            ),
            (
                "contextlib",
                "contextmanager turns a generator into a context manager for small helpers.",
            ),
        ),
    ),
    _md(
        "Enumerations",
        (
            (
                "Literal vs Enum",
                "Literal is enough for a closed string set in APIs. "
                "Enum fits when you need members.",
            ),
            (
                "Values",
                "Store enum values as strings in JSON. Do not persist auto integers.",
            ),
        ),
    ),
    _md(
        "Set versus list",
        (
            (
                "Membership",
                "A set answers 'is this item present' in average constant time. A list scans.",
            ),
            (
                "Order",
                "Lists keep insertion order for sequences. "
                "Sets drop duplicates and do not teach order.",
            ),
        ),
    ),
    _md(
        "JSON Schema",
        (
            (
                "Constrained decoding",
                "JSON Schema in Ollama format keeps local models inside a fixed object shape.",
            ),
            (
                "required fields",
                "List required keys so the decoder cannot omit order or quizzes.",
            ),
        ),
    ),
    _md(
        "Timezones",
        (
            (
                "Store UTC",
                "Backend stores aware datetime in UTC. Display converts with astimezone.",
            ),
            (
                "Naive trap",
                "datetime.now() without tz is naive and cannot compare with aware values.",
            ),
        ),
    ),
)


def eval_article_count() -> int:
    return len(EVAL_ARTICLES)
