from __future__ import annotations


def test_run_lab_dry_run_passes(lab_runner_modules) -> None:
    config, runner = lab_runner_modules
    settings = config.LabRunnerSettings(
        rabbitmq_url="",
        lab_jobs_queue="lab.jobs",
        grading_service_url="http://grading:8004",
        dry_run=True,
        default_timeout_seconds=30,
    )
    step = {
        "kind": "lab",
        "compose_file": "lab/compose.yaml",
        "checks": [{"type": "command", "command": "true"}],
    }
    outcome = runner.run_lab(settings, pack_root="/tmp/unused", step=step)
    assert outcome.passed is True
    assert outcome.details.get("mode") == "dry_run"
