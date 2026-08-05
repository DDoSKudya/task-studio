from __future__ import annotations

from app.domain.course_from_article.normalize_practice import _one_code_task
from app.domain.course_from_article.practice_routing import (
    infer_course_runtime,
    is_cli_ops_course,
    is_python_dockerfile_shim,
    should_use_open_practice,
)


def test_docker_habr_article_routes_to_open_practice() -> None:
    title = "Изучаем Docker, часть 1: основы"
    corpus = (
        "Dockerfile содержит инструкции. docker run image_name. "
        "docker build -t my-python-app . "
        "образ контейнера docker hub " * 3
    )
    assert is_cli_ops_course(title=title, corpus=corpus)
    assert should_use_open_practice(title=title, corpus=corpus, domain="code")


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


def test_python_dockerfile_shim_detected() -> None:
    template = (
        "def create_dockerfile(path: str) -> str:\n"
        '    return """\nFROM python:3.12-slim\nWORKDIR /app\n"""\n'
    )
    assert is_python_dockerfile_shim(template=template, content="Создайте Docker-образ")


def test_normalize_converts_dockerfile_shim_to_open_task() -> None:
    task = _one_code_task(
        {
            "id": "code-easy",
            "title": "Docker image",
            "content": "Создайте Dockerfile",
            "template": (
                "def create_dockerfile(path_to_requirements: str) -> str:\n"
                '    return "FROM python:3.12-slim\\n"\n'
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
    assert "Dockerfile" in str(task["content"])
