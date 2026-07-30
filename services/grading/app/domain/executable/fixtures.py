from __future__ import annotations

SUPPORTED_IO_RUNTIMES = frozenset(
    {
        "python",
        "python3",
        "javascript",
        "js",
        "node",
        "typescript",
        "ts",
        "go",
        "golang",
        "sql",
        "sqlite3",
        "bash",
        "sh",
    }
)

_FAKE_OBJECT_TOKENS = frozenset(
    {
        "mock_session",
        "session",
        "mock",
        "db",
        "conn",
        "connection",
        "client",
        "cursor",
        "engine",
    }
)


def args_need_fixtures(args: list[object]) -> bool:
    for value in args:
        if isinstance(value, dict) and "$call" in value:
            return True
        if isinstance(value, str):
            token = value.strip().casefold()
            if token in _FAKE_OBJECT_TOKENS or token.startswith("mock_"):
                return True
    return False
