from __future__ import annotations

from app.config import StudioApiSettings

SUPPORTED_LSP = frozenset({"pyright", "typescript", "gopls", "sqls"})


class LspTarget:
    __slots__ = ("host", "port")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


def lsp_target(settings: StudioApiSettings, language: str) -> LspTarget | None:
    match language:
        case "pyright":
            return LspTarget(settings.lsp_pyright_host, settings.lsp_pyright_port)
        case "typescript":
            return LspTarget(settings.lsp_typescript_host, settings.lsp_typescript_port)
        case "gopls":
            return LspTarget(settings.lsp_gopls_host, settings.lsp_gopls_port)
        case "sqls":
            return LspTarget(settings.lsp_sqls_host, settings.lsp_sqls_port)
        case _:
            return None


def runtime_for_lsp(language: str) -> str | None:
    match language:
        case "pyright":
            return "python"
        case "typescript":
            return "javascript"
        case "gopls":
            return "go"
        case "sqls":
            return "sql"
        case _:
            return None
