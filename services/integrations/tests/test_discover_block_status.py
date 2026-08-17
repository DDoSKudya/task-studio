from __future__ import annotations

from types import SimpleNamespace

from app.api.routes.discovery.discover_block_status import resolve_platform_catalog_state


def test_stepik_ready_without_credentials_when_public_import_allowed() -> None:
    adapter = SimpleNamespace(
        info=SimpleNamespace(
            id="stepik",
            capabilities=SimpleNamespace(
                search_catalog=True,
                import_course=True,
                requires_auth=True,
                import_without_auth=True,
            ),
            auth=SimpleNamespace(settings_fields=["username", "password"]),
        )
    )
    status, message, courses = resolve_platform_catalog_state(
        adapter,
        credentials={},
        error=None,
        remote=[],
    )
    assert status == "ready"
    assert "import public" in (message or "")
    assert courses == []
