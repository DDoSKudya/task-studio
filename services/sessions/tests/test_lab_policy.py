from __future__ import annotations

from app.domain.lab.session_lab_policy import lab_should_sync_llm


def test_compose_file_uses_async_lab() -> None:
    assert lab_should_sync_llm({"kind": "lab", "compose_file": "lab/compose.yaml"}) is False


def test_explicit_llm_checker_stays_sync() -> None:
    assert (
        lab_should_sync_llm({"kind": "lab", "compose_file": "lab/compose.yaml", "checker": "llm"})
        is True
    )


def test_image_lab_uses_async() -> None:
    assert lab_should_sync_llm({"kind": "lab", "lab": {"image": "python:3.12"}}) is False


def test_missing_compose_and_image_falls_back_to_llm() -> None:
    assert lab_should_sync_llm({"kind": "lab", "checks": []}) is True
