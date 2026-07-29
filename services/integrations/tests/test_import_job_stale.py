from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from integrations_helpers.loaders import load_integrations_module


def test_import_job_stale_and_republish_thresholds() -> None:
    jobs = load_integrations_module("app.domain.jobs")
    now = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)

    pending_fresh = SimpleNamespace(status="pending", created_at=now - timedelta(seconds=20))
    pending_republish = SimpleNamespace(status="pending", created_at=now - timedelta(seconds=60))
    pending_stale = SimpleNamespace(status="pending", created_at=now - timedelta(minutes=16))
    fetching_fresh = SimpleNamespace(status="fetching", created_at=now - timedelta(minutes=2))
    fetching_stale = SimpleNamespace(status="fetching", created_at=now - timedelta(minutes=7))

    assert jobs.import_job_is_stale(pending_fresh, now=now) is False
    assert jobs.import_job_is_stale(pending_stale, now=now) is True
    assert jobs.import_job_is_stale(fetching_fresh, now=now) is False
    assert jobs.import_job_is_stale(fetching_stale, now=now) is True

    assert jobs.import_job_needs_republish(pending_fresh, now=now) is False
    assert jobs.import_job_needs_republish(pending_republish, now=now) is True
    assert jobs.import_job_needs_republish(fetching_fresh, now=now) is False


def test_heal_helpers_exported() -> None:
    jobs = load_integrations_module("app.domain.jobs")
    assert "force" in jobs.create_import_job.__code__.co_varnames
    assert callable(jobs.fail_stale_import_jobs)
    assert callable(jobs.supersede_active_import_jobs)
