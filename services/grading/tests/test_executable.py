from __future__ import annotations

from app.domain.executable import step_tests_are_executable


def test_pure_python_io_is_executable() -> None:
    assert step_tests_are_executable(
        {
            "runtime": "python",
            "tests": [{"input": [1, 2], "output": 3}],
        }
    )


def test_mock_session_without_setup_not_executable() -> None:
    assert not step_tests_are_executable(
        {
            "runtime": "python",
            "tests": [{"input": ["mock_session", "a@b.c"], "output": 1}],
        }
    )


def test_setup_and_call_fixture_is_executable() -> None:
    assert step_tests_are_executable(
        {
            "runtime": "python",
            "setup": "def make_session():\n    return object()\n",
            "tests": [{"input": [{"$call": "make_session"}, "a@b.c"], "output": 1}],
        }
    )


def test_scripted_run_is_executable() -> None:
    assert step_tests_are_executable(
        {
            "runtime": "python",
            "tests": [{"run": "assert True"}],
        }
    )


def test_checker_llm_forces_non_executable() -> None:
    assert not step_tests_are_executable(
        {
            "checker": "llm",
            "runtime": "python",
            "tests": [{"input": [1], "output": 1}],
        }
    )


def test_unsupported_runtime_not_executable() -> None:
    assert not step_tests_are_executable(
        {
            "runtime": "rust",
            "tests": [{"input": [1], "output": 1}],
        }
    )
