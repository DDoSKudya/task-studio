from __future__ import annotations

from app.domain.course_from_article.practice.normalize_practice import _one_code_task
from app.domain.course_from_article.practice.practice_routing import (
    infer_course_runtime,
    is_command_oriented_course,
    is_python_artifact_shim,
    should_use_open_practice,
)


def test_command_workflow_keeps_executable_practice() -> None:
    title = "Командная строка для развёртывания"
    corpus = (
        "Конфигурация задаётся в manifest.yml.\n"
        "```shell\nplatform-cli build --tag release\n"
        "platform-cli deploy --file manifest.yml\n```"
    )
    assert is_command_oriented_course(title=title, corpus=corpus)
    assert not should_use_open_practice(title=title, corpus=corpus, domain="code")
    assert infer_course_runtime(title=title, corpus=corpus) == ("bash", "5.2.0")


def test_java_article_infers_java_runtime() -> None:
    runtime, version = infer_course_runtime(
        title="Spring Boot basics",
        corpus="public class App { public static void main(String[] args) {} }",
        fallback="python",
    )
    assert runtime == "java"
    assert version == "15.0.2"


def test_python_article_keeps_python_runtime() -> None:
    runtime, _ = infer_course_runtime(
        title="Python decorators",
        corpus="def decorator(fn):\n    def wrapper():\n        pass\n",
        fallback="python",
    )
    assert runtime == "python"


def test_history_course_uses_open_practice_even_if_domain_code() -> None:
    title = "История культуры Серебряного века"
    corpus = "Философия и литература эпохи. Гуманитарное чтение поэмы и романа."
    assert should_use_open_practice(
        title=title,
        corpus=corpus,
        domain="code",
        profile="humanities",
    )
    assert not should_use_open_practice(
        title="FastAPI path operations",
        corpus="from fastapi import FastAPI\ndef read_item():\n    pass\n",
        domain="code",
        profile="programming",
    )


def test_python_artifact_shim_detected() -> None:
    template = (
        'def create_manifest(path: str) -> str:\n    return """\nservice: api\nreplicas: 2\n"""\n'
    )
    assert is_python_artifact_shim(
        template=template,
        content="Создайте манифест конфигурации",
    )


def test_normalize_converts_artifact_shim_to_open_task() -> None:
    task = _one_code_task(
        {
            "id": "code-easy",
            "title": "Манифест сервиса",
            "content": "Создайте манифест deployment.yml",
            "template": (
                "def create_manifest(service_name: str) -> str:\n"
                '    return "service: api\\nreplicas: 2\\n"\n'
            ),
            "tests": [],
            "checker": "llm",
        },
        index=0,
        runtime="python",
        runtime_version="3.12",
    )
    assert task is not None
    assert task["kind"] == "task"
    assert "манифест" in str(task["content"]).casefold()
