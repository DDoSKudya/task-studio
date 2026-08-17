from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from studio_contracts.api.studio_schemas import CourseDepth, CourseFromArticleRequest
from tutor_helpers.loaders import load_service_module

_FASTAPI_MD = """
# Introduction to FastAPI

FastAPI is a Python web framework for building APIs with type hints and OpenAPI.
It validates request bodies through Pydantic models and documents routes automatically.

# Path operations

A path operation is a function decorated with @app.get or @app.post.
The decorator binds an HTTP method and URL path to a Python callable that returns JSON.

# Dependency injection

Depends injects shared resources such as a database session into path operations.
The same dependency can be reused across routers without copying setup code.
""".strip()

_ROUTERS_MD = """
# APIRouter packages

APIRouter groups related HTTP routes in a package so imports stay tidy.
Each router owns a prefix and a set of path operations that belong together.

# Avoid circular imports

Keep router imports acyclic so packages load without circular graphs.
Import the router from the package init only after the route modules exist.
""".strip()


def test_inventory_covers_headings_from_two_sources() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    seeds = inventory.inventory_from_sources(
        [
            {"title": "FastAPI basics", "content": _FASTAPI_MD},
            {"title": "Routers", "content": _ROUTERS_MD},
        ],
        sentences_per_window=3,
    )
    titles = " ".join(seed.title for seed in seeds)
    assert "Introduction to FastAPI" in titles
    assert "Path operations" in titles
    assert "Dependency injection" in titles
    assert "APIRouter packages" in titles
    assert "Avoid circular imports" in titles
    assert all(seed.excerpt.strip() for seed in seeds)


def test_split_source_units_keeps_all_headings() -> None:
    sections = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    chunks = [
        f"## Topic {index}\n" + ("Substantial teaching paragraph about the topic. " * 8)
        for index in range(8)
    ]
    units = sections.split_source_units("\n\n".join(chunks), sentences_per_window=3)
    assert len(units) >= 8
    joined = "\n".join(units)
    assert "Topic 0" in joined
    assert "Topic 7" in joined


def test_collapse_keeps_unique_topics_when_wanted_is_smaller() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    seeds = inventory.inventory_from_sources(
        [
            {"title": "FastAPI basics", "content": _FASTAPI_MD},
            {"title": "Routers", "content": _ROUTERS_MD},
        ],
        sentences_per_window=3,
    )
    fitted = collapse.fit_seed_count(seeds, max_chapters=100)
    titles = [seed.title for seed in fitted]
    assert len(fitted) >= 5
    assert "Introduction to FastAPI" in titles
    assert "APIRouter packages" in titles


def _docker_section(topic: str) -> str:
    return (
        f"## Как устроены {topic}\n"
        f"Начнём с того, зачем в проекте нужны {topic} и какую задачу они закрывают. "
        f"Дальше посмотрим, как настроить {topic} в компоуз-файле без ручных команд. "
        f"Отдельно разберём, почему {topic} ломаются после переезда на другой хост."
    )


def test_shell_titles_cover_article_wrappers() -> None:
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    for wrapper in (
        "Тема",
        "Вводная информация",
        "Общая информация",
        "Что изучать дальше",
        "Заключение и где искать практику и знания?",
        "Полезные ссылки",
        "Введение",
        "Практические примеры",
        "База теории",
        "Дополнительные ресурсы",
        "Полезные ресурсы",
        "Объяснение",
        "Explanation",
        "Additional resources",
        "Fast, consistent delivery of your applications",
        "Build, Ship and Run Any Service, Anywhere",
        "Students On Software Architecture",
        "Переход к следующему разделу",
        "Далее - Архитектура Docker",
        "Плохой пример",
        "Хороший пример",
        "Bad example",
        "Good example",
    ):
        assert collapse.is_shell_title(wrapper), wrapper
    assert not collapse.is_shell_title("Development Process")
    assert not collapse.is_shell_title("Stakeholders")
    assert not collapse.is_shell_title("Metrics")
    assert not collapse.is_shell_title("Заинтересованные стороны")
    assert not collapse.is_shell_title("Поддержка Windows-контейнеров")
    assert not collapse.is_shell_title("Метрики контейнеров в Prometheus")
    for topic in (
        "Введение в Docker",
        "Основные понятия Docker",
        "Сеть контейнеров",
        "Хранилища образов: Docker Hub и Registry",
    ):
        assert not collapse.is_shell_title(topic), topic


def test_subject_sections_are_not_dropped_by_topic_or_source_metadata() -> None:
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    stakeholders = inventory.TopicSeed(
        title="Заинтересованные стороны",
        objective="перечислить стейкхолдеров",
        excerpt=(
            "### Stakeholders\n\nStakeholders play a crucial role in the design of software. " * 6
        ),
        source_title="Docker",
        order=0,
        from_heading=True,
    )
    cover = inventory.TopicSeed(
        title="Один контейнер — один приложение",
        objective="описать принцип",
        excerpt=(
            "# Distributed systems field report\n\n"
            "**Alex Smith**\n\n*Technical University*\n\n"
            "The platform coordinates independent services. " * 8
        ),
        source_title="Field report",
        order=1,
        from_heading=True,
    )
    assert not collapse.is_shell_seed(stakeholders)
    assert not collapse.is_shell_seed(cover)


def test_navigation_is_shell_but_architecture_content_is_teachable() -> None:
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    next_steps = inventory.TopicSeed(
        title="Основные принципы использования",
        objective="подсказать следующие шаги",
        excerpt=(
            "## Что изучать дальше\n\n"
            "Следующие шаги зависят от того, что вы хотите делать дальше. " * 6
        ),
        source_title="Platform",
        order=0,
        from_heading=True,
    )
    software_arch = inventory.TopicSeed(
        title="Архитектура",
        objective="описать архитектуру",
        excerpt=(
            "## Architecture\n\n"
            "An integral part of software production is designing the architecture. " * 6
        ),
        source_title="Platform",
        order=1,
        from_heading=True,
    )
    assert collapse.is_shell_seed(next_steps)
    assert not collapse.is_shell_seed(software_arch)


def test_docker_docs_chrome_alone_is_not_shell() -> None:
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    seed = inventory.TopicSeed(
        title="The Docker platform",
        objective="объяснить контейнеры",
        excerpt=(
            "# What is Docker?\n\nAsk Gordon\n\nTable of contents\n\n"
            "Docker is an open platform for developing, shipping, and running applications. "
            "Docker enables you to separate your applications from your infrastructure. " * 4
        ),
        source_title="What is Docker?",
        order=0,
        from_heading=True,
    )
    assert not collapse.is_shell_seed(seed)
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    seed = inventory.TopicSeed(
        title="Практические примеры",
        objective="повторить вывод статьи",
        excerpt=(
            "## Conclusion\n\nDocker is a product designed to make life easier for developers. " * 8
        ),
        source_title="Docker",
        order=0,
        from_heading=True,
    )
    assert collapse.is_shell_seed(seed)


def test_example_captions_do_not_become_chapters() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    dockerfile_md = "\n\n".join(
        [
            "## Слои и кэш",
            "Каждая инструкция Dockerfile создаёт слой. " * 6,
            "### Плохо — три слоя, кэш apt остаётся в образе навсегда",
            "```dockerfile\nRUN apt-get update\nRUN apt-get install -y curl\n```",
            "Кэш пакетов уезжает в образ и остаётся там навсегда. " * 6,
            "### Хорошо — один слой, кэш удалён в той же команде",
            "```dockerfile\nRUN apt-get update && apt-get install -y curl"
            " && rm -rf /var/lib/apt/lists/*\n```",
            "Одна инструкция собирает и подчищает за собой. " * 6,
        ]
    )

    seeds = inventory.inventory_from_sources(
        [{"title": "Сборка образов", "content": dockerfile_md}],
        sentences_per_window=3,
    )

    headings = [seed.title for seed in seeds if seed.from_heading]
    assert "Слои и кэш" in headings
    assert not any(title.startswith(("Плохо", "Хорошо")) for title in headings)
    caption = "### Плохо — три слоя, кэш apt остаётся в образе навсегда\n```dockerfile\nRUN x\n```"
    assert inventory.heading_of_unit(caption).startswith("Плохо")
    assert not inventory.section_heading(caption, source_title="Сборка образов")


def test_article_cover_heading_is_not_a_chapter() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    article = "\n\n".join(
        [
            "# Что такое Docker простыми словами",
            "Docker упаковывает приложение вместе с зависимостями. " * 6,
            "## Образы и контейнеры",
            "Образ — это шаблон, контейнер — запущенный экземпляр образа. " * 6,
        ]
    )

    seeds = inventory.inventory_from_sources(
        [{"title": "Что такое Docker простыми словами", "content": article}],
        sentences_per_window=3,
    )

    headings = [seed.title for seed in seeds if seed.from_heading]
    assert "Образы и контейнеры" in headings
    assert "Что такое Docker простыми словами" not in headings


def test_order_puts_foundations_before_advanced() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    intro = inventory.TopicSeed(
        title="Introduction to routing",
        objective="start",
        excerpt="intro text " * 20,
        source_title="A",
        order=2,
    )
    advanced = inventory.TopicSeed(
        title="Production pitfalls",
        objective="hard",
        excerpt="prod text " * 20,
        source_title="A",
        order=0,
    )
    middle = inventory.TopicSeed(
        title="Path operations",
        objective="mid",
        excerpt="path text " * 20,
        source_title="A",
        order=1,
    )
    ordered = compiler.order_seeds_heuristic([advanced, middle, intro])
    assert ordered[0].title.startswith("Introduction")
    assert ordered[-1].title.startswith("Production")


def test_order_places_foundation_before_reference_and_advanced_topics() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    glossary = inventory.TopicSeed(
        title="Основные понятия потоков: краткий справочник",
        objective="terms",
        excerpt="glossary " * 20,
        source_title="A",
        order=0,
    )
    what_is = inventory.TopicSeed(
        title="What is event streaming?",
        objective="intro",
        excerpt="event streaming is " * 20,
        source_title="B",
        order=1,
    )
    advanced = inventory.TopicSeed(
        title="Production pitfalls and scaling",
        objective="operate",
        excerpt="advanced operations " * 20,
        source_title="C",
        order=2,
    )
    ordered = compiler.order_seeds_heuristic([glossary, what_is, advanced])
    titles = [seed.title for seed in ordered]
    assert titles[0].startswith("What is event streaming")
    assert titles.index(glossary.title) > titles.index(what_is.title)
    assert titles[-1].startswith("Production pitfalls")


def test_stabilize_book_order_pins_wrapups() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    wrap = inventory.TopicSeed(
        title="Подведение итогов",
        objective="recap",
        excerpt="summary " * 20,
        source_title="A",
        order=0,
    )
    mid = inventory.TopicSeed(
        title="Партиции",
        objective="mid",
        excerpt="parts " * 20,
        source_title="A",
        order=1,
    )
    intro = inventory.TopicSeed(
        title="Что такое Kafka и зачем она нужна",
        objective="why",
        excerpt="why " * 20,
        source_title="A",
        order=2,
    )
    ordered = compiler.stabilize_book_order([wrap, mid, intro])
    assert ordered[-1].title.startswith("Подведение")
    assert "Партиции" in {seed.title for seed in ordered[:-1]}
    assert "Что такое Kafka и зачем она нужна" in {seed.title for seed in ordered[:-1]}


def test_merge_shell_seeds_drops_bare_intro() -> None:
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    shell = inventory.TopicSeed(
        title="Введение",
        objective="intro",
        excerpt="shell text about kafka basics " * 10,
        source_title="A",
        order=0,
    )
    body = inventory.TopicSeed(
        title="Топики и партиции",
        objective="topics",
        excerpt="body text " * 20,
        source_title="A",
        order=1,
    )
    fitted = collapse.fit_seed_count([shell, body], max_chapters=10)
    assert len(fitted) == 1
    assert fitted[0].title == "Топики и партиции"
    assert "shell text" in fitted[0].excerpt


def test_headingless_source_derives_titles_from_window_claims() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    strategies = load_service_module("app.domain.course_strategies")
    plain = " ".join(
        f"Сейчас система поддерживает разные режимы и вариант номер {index} тоже работает."
        for index in range(30)
    )
    seeds = inventory.inventory_from_sources(
        [{"title": "Redis в продакшене", "content": plain}],
        sentences_per_window=3,
    )
    assert seeds
    assert not any(seed.from_heading for seed in seeds)
    for seed in seeds:
        assert strategies.chapter_title_is_valid(seed.title), seed.title
        assert not seed.title.endswith((")", "часть"))
        assert "Система поддерживает разные режимы" in seed.title


def test_merge_prefers_real_heading_over_generated_label() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    generated = inventory.TopicSeed(
        title="Redis в продакшене (4) длинная подпись",
        objective="mid",
        excerpt="Текст без заголовка. " * 20,
        source_title="Redis в продакшене",
        order=0,
        from_heading=False,
    )
    headed = inventory.TopicSeed(
        title="Персистентность",
        objective="mid",
        excerpt="Текст раздела. " * 20,
        source_title="Redis в продакшене",
        order=1,
        from_heading=True,
    )
    fitted = collapse.merge_adjacent_to_cap([generated, headed], cap=1)
    assert fitted[0].title == "Персистентность"


def test_merge_excerpts_drops_repeated_boundary_sentence() -> None:
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    shared = "В отличие от RDB, AOF не блокирует Redis."
    merged = collapse.merge_excerpts(
        f"Журнал операций дописывается в конец файла. {shared}",
        f"{shared} У режима есть и недостатки.",
    )
    assert merged.count(shared) == 1
    assert "У режима есть и недостатки." in merged


def test_prepare_corpus_removes_cross_source_semantic_duplicates() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    repeated = (
        "Redis Sentinel следит за ведущим узлом и запускает автоматическое "
        "переключение при его недоступности."
    )
    seeds = [
        inventory.TopicSeed(
            title="Sentinel и отказоустойчивость",
            objective="Разобрать автоматическое переключение",
            excerpt=f"{repeated} Клиенты узнают адрес нового ведущего узла.",
            source_title="Документация",
            order=0,
            from_heading=True,
        ),
        inventory.TopicSeed(
            title="Мониторинг ведущего узла",
            objective="Настроить наблюдение Sentinel",
            excerpt=f"{repeated} Кворум определяет начало переключения.",
            source_title="Практическое руководство",
            order=1,
            from_heading=True,
        ),
    ]

    prepared = collapse.prepare_corpus(seeds, max_chapters=20)

    joined = "\n".join(seed.excerpt for seed in prepared)
    assert joined.count(repeated) == 1
    assert "Клиенты узнают адрес" in joined
    assert "Кворум определяет" in joined


def test_prepare_corpus_merges_thin_headingless_windows() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    seeds = [
        inventory.TopicSeed(
            title=f"Redis в продакшене ({index})",
            objective=f"Разобрать шаг {index}",
            excerpt=(f"Шаг {index} объясняет настройку Redis. " * 8).strip(),
            source_title="Redis в продакшене",
            order=index,
        )
        for index in range(6)
    ]

    prepared = collapse.prepare_corpus(seeds, max_chapters=100)

    assert len(prepared) < len(seeds)
    assert all(len(seed.excerpt) >= 1_000 for seed in prepared[:-1])
    assert all(f"Шаг {index}" in "\n".join(seed.excerpt for seed in prepared) for index in range(6))


def test_quiz_must_cite_chapter_theory() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    theory = "APIRouter groups related HTTP routes in a package."
    grounded = {
        "question": "What does APIRouter group in a FastAPI package?",
        "choices": ["Related HTTP routes", "GPU kernels", "CSS files", "DNS records"],
        "answer": 0,
    }
    generic = {
        "question": "Which statement matches the article overall?",
        "choices": [
            "matches the article",
            "opposite of the article",
            "unrelated detail",
            "too vague to verify",
        ],
        "answer": 0,
    }
    assert heuristics.quiz_item_is_usable(grounded, theory=theory, locale="en")
    assert not heuristics.quiz_item_is_usable(generic, theory=theory, locale="en")
    assert not heuristics.quiz_item_is_usable(grounded, theory=theory, locale="ru")


def test_practice_spec_allows_empty_starter_for_humanities() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    task = {
        "title": "Сравни две трактовки реформы",
        "content": (
            "Сравни две трактовки реформы из главы и укажи, чем они расходятся по причине."
        ),
        "template": "",
    }
    assert heuristics.practice_spec_is_usable(task, locale="ru", require_starter=False)
    assert not heuristics.practice_spec_is_usable(task, locale="ru", require_starter=True)


def test_practice_spec_accepts_tutorial_step_without_contest_labels() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    drill = {
        "title": "Write a path operation",
        "content": "Add a GET /health path operation on the FastAPI app from this chapter.",
        "template": "from fastapi import FastAPI\napp = FastAPI()\n",
    }
    contest = {
        "title": "Write a path operation",
        "content": (
            "Given: a FastAPI app. Expected: GET /health returns 200. Constraints: no extra routes."
        ),
        "template": "from fastapi import FastAPI\napp = FastAPI()\n",
    }
    thin = {
        "title": "Write a path operation",
        "content": "Write a small FastAPI example that demonstrates routing.",
        "template": "from fastapi import FastAPI\napp = FastAPI()\n",
    }
    assert heuristics.practice_spec_is_usable(drill, locale="en")
    assert heuristics.practice_spec_is_usable(contest, locale="en")
    assert not heuristics.practice_spec_is_usable(contest, locale="ru")
    assert not heuristics.practice_spec_is_usable(thin, locale="en")


def test_practice_spec_accepts_rezultat_and_rewrites_solve() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    task = {
        "title": "Эндпоинт FastAPI health",
        "content": (
            "Дано: приложение FastAPI. Результат: GET /health отвечает 200. "
            "Ограничения: без лишних маршрутов."
        ),
        "template": "from fastapi import FastAPI\n\ndef solve():\n    ...\n",
    }
    assert heuristics.practice_spec_is_usable(task, locale="ru")
    normalized = heuristics.normalize_practice_task(task)
    assert "def solve(" not in str(normalized["template"])
    assert "def fastapi(" in str(normalized["template"])


def test_practice_salvages_empty_template_from_theory_fence() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    theory = (
        "Вынеси declarative_base в settings.\n```python\nfrom app.db.settings import Base\n```\n"
    )
    task = {
        "title": "Импортируем Base из файла настроек БД",
        "content": ("Импортируй Base из нашего файла настроек БД, который мы исправили ранее."),
        "template": "",
    }
    assert heuristics.practice_spec_is_usable(task, locale="ru", theory=theory)
    normalized = heuristics.normalize_practice_task(task, theory=theory)
    assert "from app.db.settings import Base" in str(normalized["template"])
    assert "Дано:" not in str(normalized["content"])
    assert "импорт" in str(normalized["content"]).casefold()


def test_practice_must_fix_lists_only_remaining_holes() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    task = {
        "title": "Эндпоинт FastAPI health",
        "content": "коротко",
        "template": "",
    }
    fixes = heuristics.practice_must_fix(task, locale="ru")
    assert any("предложени" in item or "sentences" in item for item in fixes)
    assert any("стартовый" in item for item in fixes)


def test_practice_content_mentioning_solve_is_not_template() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    task = {
        "title": "Собери роутер пакета",
        "content": (
            "Дано: пакет приложения. Ожидается: функция build_router. "
            "Не используй def solve(). Ограничения: без циклов импорта."
        ),
        "template": "from fastapi import APIRouter\n\ndef build_router(name: str):\n    ...\n",
    }
    assert heuristics.practice_spec_is_usable(task, locale="ru")


def test_practice_spec_accepts_russian_imperative_io() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    task = {
        "title": "Собери роутер пакета",
        "content": (
            "Напиши функцию build_router. Она принимает имя пакета. "
            "Верни APIRouter с префиксом. Ограничения: без циклов импорта."
        ),
        "template": "from fastapi import APIRouter\n\ndef build_router(name: str):\n    ...\n",
    }
    assert heuristics.practice_spec_is_usable(task, locale="ru")
    assert not heuristics.practice_spec_is_usable(task, locale="en")
    fenced = heuristics.starter_from_brief(
        "Дано: пакет.\n```python\nfrom fastapi import APIRouter\n```"
    )
    assert "APIRouter" in fenced


def test_template_practice_includes_io_markers() -> None:
    fallbacks = load_service_module("app.domain.course_from_article.local_course.content.fallbacks")
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    tasks = fallbacks.template_practice_from_objective(
        chapter={"id": "ch1", "title": "Routers", "objective": "Split routers by package"},
        count=1,
        topic_key="topic-routers",
        runtime="python",
    )
    assert heuristics.practice_spec_is_usable(tasks[0]) is False


def test_compiler_checkpoint_roundtrip(tmp_path: Path) -> None:
    store_mod = load_service_module("app.domain.course_build.store")
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "FastAPI"},
        title="FastAPI",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    chapters = [
        {
            "id": "t1",
            "title": "Introduction to FastAPI",
            "objective": "Know the framework",
            "source_excerpt": "FastAPI is a Python web framework.",
        }
    ]
    store.save_compiler(user_id, build_id, {"chapters": chapters, "outcomes": ["learn FastAPI"]})
    loaded = store.load_compiler(user_id, build_id)
    assert loaded is not None
    assert loaded["chapters"][0]["title"] == "Introduction to FastAPI"


def test_mark_build_done_keeps_files_until_discard(tmp_path: Path) -> None:
    store_mod = load_service_module("app.domain.course_build.store")
    checkpoint = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_checkpoint"
    )
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "FastAPI"},
        title="FastAPI",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    store.save_topic(
        user_id,
        build_id,
        "t1",
        theory={"id": "th1", "content": "body"},
        quizzes=[],
        codes=[],
    )
    checkpoint.mark_build_done(store, user_id=user_id, build_id=build_id)
    assert store.exists(user_id, build_id)
    assert store.load_meta(user_id, build_id).status == "done"
    assert store.list_for_user(user_id, include_done=True)
    store.discard(user_id, build_id)
    assert not store.exists(user_id, build_id)


def test_done_build_can_reassemble_from_checkpoint(tmp_path: Path) -> None:
    store_mod = load_service_module("app.domain.course_build.store")
    checkpoint = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_checkpoint"
    )
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "FastAPI", "article": "x" * 80, "include_theory": True},
        title="FastAPI",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    store.patch_meta(user_id, build_id, status="done", stage="done")
    config = SimpleNamespace(course_builds_root=tmp_path, course_build_ttl_days=30)
    body = CourseFromArticleRequest(build_id=build_id)
    _store, resumed_meta, _restored, is_resume = checkpoint.resolve_build_session(
        config,
        user_id=user_id,
        body=body,
    )
    assert is_resume is True
    assert resumed_meta.status == "running"
    assert store.exists(user_id, build_id)


def test_prune_removes_done_and_keeps_paused(tmp_path: Path) -> None:
    store_mod = load_service_module("app.domain.course_build.store")
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    done = store.create(
        user_id=user_id,
        request_payload={"title": "Done"},
        title="Done",
        mode="topic_bundles",
    )
    paused = store.create(
        user_id=user_id,
        request_payload={"title": "Paused"},
        title="Paused",
        mode="topic_bundles",
    )
    store.patch_meta(user_id, uuid.UUID(done.build_id), status="done", stage="done")
    store.patch_meta(user_id, uuid.UUID(paused.build_id), status="paused", stage="topic_bundle")
    assert store.prune_expired(user_id) == 0
    assert store.exists(user_id, uuid.UUID(done.build_id))
    assert store.exists(user_id, uuid.UUID(paused.build_id))

    meta_path = tmp_path / str(user_id) / done.build_id / "meta.json"
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    raw["updated_at"] = "2020-01-01T00:00:00Z"
    meta_path.write_text(json.dumps(raw), encoding="utf-8")
    removed = store.prune_expired(user_id)
    assert removed >= 1
    assert not store.exists(user_id, uuid.UUID(done.build_id))
    assert store.exists(user_id, uuid.UUID(paused.build_id))


def test_syllabus_from_sources_does_not_need_llm() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    seeds = inventory.inventory_from_sources(
        [
            {"title": "FastAPI basics", "content": _FASTAPI_MD},
            {"title": "Routers", "content": _ROUTERS_MD},
        ],
        sentences_per_window=3,
    )
    fitted = collapse.fit_seed_count(seeds, max_chapters=100)
    chapters = compiler.seeds_to_chapters(fitted, max_chapters=100)
    body = CourseFromArticleRequest(article=_FASTAPI_MD, title="FastAPI course", locale="en")
    outline_mod = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_analyze"
    )
    outline = outline_mod.AnalyzeStageResult()
    compiler.apply_syllabus_to_outline(
        outline,
        body=body,
        article=_FASTAPI_MD,
        chapters=chapters,
        outcomes=["use FastAPI routers"],
    )
    assert outline.chapters
    assert any("APIRouter" in item["source_excerpt"] for item in outline.chapters)
    assert outline.pack_id
    assert outline.book_spine["address"] == "you"
    assert outline.book_spine["throughline"]
    assert (
        "fastapi" in outline.book_spine["throughline"].casefold()
        or " → " in outline.book_spine["throughline"]
    )


def test_local_book_spine_uses_chapter_arc() -> None:
    spine_mod = load_service_module("app.domain.course_from_article.local_course.curriculum.spine")
    spine = spine_mod.build_local_book_spine(
        locale="ru",
        title="Курс",
        chapters=[{"title": "Роутеры"}, {"title": "Сессии"}],
        outcomes=["собрать API"],
    )
    assert spine["throughline"] == "собрать API"
    assert spine["address"] == "ты"
    merged = spine_mod.merge_book_spine(
        {"throughline": "Роутеры", "voice": "", "address": ""},
        locale="ru",
        title="Курс",
        chapters=[{"title": "Роутеры"}, {"title": "Сессии"}],
        outcomes=[],
    )
    assert " → " in merged["throughline"]


def test_parse_json_object_strips_markdown_fences() -> None:
    schemas = load_service_module("app.domain.course_from_article.local_course.policy.schemas")
    payload = schemas.parse_json_object('```json\n{"order": ["1", "0"], "outcomes": []}\n```')
    assert payload["order"] == ["1", "0"]


def test_parse_json_object_extracts_from_prose_wrapper() -> None:
    schemas = load_service_module("app.domain.course_from_article.local_course.policy.schemas")
    payload = schemas.parse_json_object(
        'Sure, here is the JSON:\n{"tasks": [{"title": "Health route"}]}\nThanks.'
    )
    assert payload["tasks"][0]["title"] == "Health route"
    items = schemas.payload_items(payload, plural="tasks", singular="task")
    assert len(items) == 1
    one = schemas.payload_items(
        {"task": {"title": "Health route", "content": "x"}},
        plural="tasks",
        singular="task",
    )
    assert one[0]["title"] == "Health route"
    flat = schemas.payload_items(
        {
            "title": "Health route",
            "content": "Add a GET /health handler that returns ok.",
            "template": "from fastapi import FastAPI\napp = FastAPI()\n",
        },
        plural="tasks",
        singular="task",
    )
    assert len(flat) == 1
    assert flat[0]["title"] == "Health route"


def test_apply_order_ids_keeps_missing_and_skips_unknown() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    seeds = [
        inventory.TopicSeed(
            title="Introduction",
            objective="start",
            excerpt="intro",
            source_title="A",
            order=0,
        ),
        inventory.TopicSeed(
            title="Middle",
            objective="mid",
            excerpt="mid",
            source_title="A",
            order=1,
        ),
        inventory.TopicSeed(
            title="Advanced",
            objective="hard",
            excerpt="hard",
            source_title="A",
            order=2,
        ),
    ]
    ordered = compiler._apply_order_ids(seeds, ["2", "9", "2"])
    assert ordered is not None
    assert [seed.title for seed in ordered] == ["Advanced", "Introduction", "Middle"]


def test_merge_semantic_groups_keeps_source_evidence_and_order() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    seeds = [
        inventory.TopicSeed(
            title="Redis Sentinel",
            objective="Разобрать мониторинг",
            excerpt="Sentinel отслеживает ведущий узел.",
            source_title="Источник A",
            order=0,
            from_heading=True,
        ),
        inventory.TopicSeed(
            title="Автоматическое переключение",
            objective="Разобрать failover",
            excerpt="Кворум Sentinel запускает переключение.",
            source_title="Источник B",
            order=1,
            from_heading=True,
        ),
        inventory.TopicSeed(
            title="Redis Cluster",
            objective="Разобрать слоты",
            excerpt="Cluster распределяет 16384 слота.",
            source_title="Источник C",
            order=2,
            from_heading=True,
        ),
    ]
    ordered = [seeds[2], seeds[0], seeds[1]]

    merged = collapse.merge_semantic_groups(seeds, ordered, [["0", "1"]])

    assert [seed.title for seed in merged] == ["Redis Cluster", "Автоматическое переключение"]
    assert "отслеживает ведущий" in merged[1].excerpt
    assert "Кворум Sentinel" in merged[1].excerpt


def test_order_message_includes_claims_and_source_anchors() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    seed = inventory.TopicSeed(
        title="Redis Sentinel",
        objective="Настроить автоматическое переключение",
        excerpt=(
            "Sentinel отслеживает ведущий узел. "
            "Кворум наблюдателей запускает автоматическое переключение."
        ),
        source_title="Руководство по Redis",
        order=0,
        from_heading=True,
    )

    prompt = messages.order_user_message([seed], locale="ru")

    assert "Руководство по Redis" in prompt
    assert "Кворум наблюдателей" in prompt
    assert "merge_groups" in prompt


@pytest.mark.asyncio
async def test_order_stage_applies_semantic_merge_groups() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    seeds = [
        inventory.TopicSeed(
            title="Redis Sentinel",
            objective="Разобрать мониторинг",
            excerpt="Sentinel отслеживает ведущий узел.",
            source_title="A",
            order=0,
            from_heading=True,
        ),
        inventory.TopicSeed(
            title="Автоматическое переключение",
            objective="Разобрать failover",
            excerpt="Кворум Sentinel запускает переключение.",
            source_title="B",
            order=1,
            from_heading=True,
        ),
        inventory.TopicSeed(
            title="Redis Cluster",
            objective="Разобрать слоты",
            excerpt="Cluster распределяет 16384 слота.",
            source_title="C",
            order=2,
            from_heading=True,
        ),
    ]
    response = SimpleNamespace(content='{"order":["2","0","1"]}')
    payload = {
        "order": ["2", "0", "1"],
        "merge_groups": [["0", "1"]],
        "outcomes": ["Настроить отказоустойчивый Redis"],
    }
    with (
        patch.object(
            compiler,
            "complete_json_chat_result",
            new=AsyncMock(return_value=response),
        ),
        patch.object(
            compiler,
            "load_json_object",
            new=AsyncMock(return_value=payload),
        ),
    ):
        ordered, outcomes = await compiler.order_seeds_with_llm(
            AsyncMock(),
            target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
            seeds=seeds,
            body=CourseFromArticleRequest(article="x" * 120, locale="ru"),
            policy=policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b"),
        )

    assert [seed.title for seed in ordered] == ["Redis Cluster", "Автоматическое переключение"]
    assert "Sentinel отслеживает" in ordered[1].excerpt
    assert "Кворум Sentinel" in ordered[1].excerpt
    assert outcomes == ["Настроить отказоустойчивый Redis"]


@pytest.mark.asyncio
async def test_compiler_resumes_unordered_checkpoint(tmp_path: Path) -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    store_mod = load_service_module("app.domain.course_build.store")
    target_mod = load_service_module("app.domain.llm.target")
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "FastAPI"},
        title="FastAPI",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    chapters = [
        {
            "id": "t2",
            "title": "Production pitfalls",
            "objective": "hard",
            "source_excerpt": "prod text " * 20,
        },
        {
            "id": "t1",
            "title": "Introduction to routing",
            "objective": "start",
            "source_excerpt": "intro text " * 20,
        },
    ]
    store.save_compiler(
        user_id,
        build_id,
        {"chapters": chapters, "outcomes": [], "ordered": False},
    )

    async def fake_order(*_args, **kwargs):
        seeds = kwargs["seeds"]
        return list(reversed(list(seeds))), ["learn routing"]

    with patch.object(compiler, "order_seeds_with_llm", new=fake_order):
        out, outcomes = await compiler.compile_local_syllabus(
            AsyncMock(),
            target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
            body=CourseFromArticleRequest(article="x" * 200, locale="en"),
            sources=[],
            article="x" * 200,
            policy=policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b"),
            store=store,
            user_id=user_id,
            build_id=build_id,
            warnings=[],
        )
    assert out[0]["title"] == "Introduction to routing"
    assert outcomes == ["learn routing"]
    saved = store.load_compiler(user_id, build_id)
    assert saved is not None
    assert saved["ordered"] is True


def test_fit_seed_count_does_not_inflate_toc() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    seeds = inventory.inventory_from_sources(
        [
            {"title": "FastAPI basics", "content": _FASTAPI_MD},
            {"title": "Routers", "content": _ROUTERS_MD},
        ],
        sentences_per_window=3,
    )
    unique = len(collapse.collapse_near_duplicates(seeds))
    fitted = collapse.fit_seed_count(seeds, max_chapters=100)
    assert len(fitted) == unique
    assert len(fitted) < 10


@pytest.mark.asyncio
async def test_compiler_rebuilds_cloned_checkpoint(tmp_path: Path) -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    store_mod = load_service_module("app.domain.course_build.store")
    target_mod = load_service_module("app.domain.llm.target")
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "FastAPI"},
        title="FastAPI",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    dump = f"{_FASTAPI_MD}\n\n{_ROUTERS_MD}"
    store.save_compiler(
        user_id,
        build_id,
        {
            "chapters": [
                {
                    "id": "t1",
                    "title": "One",
                    "objective": "a",
                    "source_excerpt": dump,
                },
                {
                    "id": "t2",
                    "title": "Two",
                    "objective": "b",
                    "source_excerpt": dump,
                },
            ],
            "outcomes": [],
            "ordered": True,
        },
    )

    async def fake_order(*_args, **kwargs):
        return list(kwargs["seeds"]), ["learn FastAPI"]

    with patch.object(compiler, "order_seeds_with_llm", new=fake_order):
        out, _outcomes = await compiler.compile_local_syllabus(
            AsyncMock(),
            target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
            body=CourseFromArticleRequest(article=dump, locale="en", title="FastAPI course"),
            sources=[
                {"title": "FastAPI basics", "content": _FASTAPI_MD},
                {"title": "Routers", "content": _ROUTERS_MD},
            ],
            article=dump,
            policy=policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b"),
            store=store,
            user_id=user_id,
            build_id=build_id,
            warnings=[],
        )
    fingerprints = {item["source_excerpt"][:240].casefold() for item in out}
    assert len(out) >= 4
    assert len(fingerprints) == len(out)


@pytest.mark.asyncio
async def test_localize_rewrites_english_titles_for_russian_course() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    chapters = [
        {
            "id": "t1",
            "title": "Path operations",
            "objective": "Learn routing basics",
            "source_excerpt": "A path operation is a decorated function.",
        }
    ]

    async def fake_json(*_args, **_kwargs):
        return SimpleNamespace(
            content=json.dumps(
                {
                    "chapters": [
                        {
                            "id": "t1",
                            "title": "Операции пути",
                            "objective": "Разобрать маршрутизацию",
                        }
                    ],
                    "outcomes": ["Маршрутизация"],
                },
                ensure_ascii=False,
            )
        )

    with patch.object(compiler, "complete_json_chat_result", new=fake_json):
        labeled, outcomes = await compiler.localize_chapter_labels(
            AsyncMock(),
            target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
            body=CourseFromArticleRequest(article="x" * 80, locale="ru"),
            chapters=chapters,
            outcomes=["Learn routing"],
            policy=policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b"),
        )
    assert labeled[0]["title"] == "Операции пути"
    assert labeled[0]["source_excerpt"].startswith("A path operation")
    assert outcomes == ["Маршрутизация"]


@pytest.mark.asyncio
async def test_localize_skips_when_titles_already_match_locale() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    chapters = [
        {
            "id": "t1",
            "title": "Операции пути",
            "objective": "Разобрать маршрутизацию приложения",
            "source_excerpt": "A path operation is a decorated function.",
        }
    ]
    mock_json = AsyncMock()
    with patch.object(compiler, "complete_json_chat_result", new=mock_json):
        labeled, _outcomes = await compiler.localize_chapter_labels(
            AsyncMock(),
            target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
            body=CourseFromArticleRequest(article="x" * 80, locale="ru"),
            chapters=chapters,
            outcomes=["Маршрутизация запросов"],
            policy=policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b"),
        )
    mock_json.assert_not_called()
    assert labeled[0]["title"] == "Операции пути"


def test_english_pack_title_yields_to_russian_chapter() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    outline_mod = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_analyze"
    )
    outline = outline_mod.AnalyzeStageResult()
    compiler.apply_syllabus_to_outline(
        outline,
        body=CourseFromArticleRequest(
            article="x" * 80, locale="ru", title="Path operations course"
        ),
        article="x" * 80,
        chapters=[
            {
                "id": "t1",
                "title": "Операции пути",
                "objective": "Разобрать маршрутизацию",
                "source_excerpt": "A path operation is a decorated function.",
            }
        ],
        outcomes=["Маршрутизация"],
    )
    assert outline.title == "Операции пути"
    assert outline.book_spine["address"] == "ты"


def test_source_title_wins_over_first_headingless_chapter_label() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    outline_mod = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_analyze"
    )
    outline = outline_mod.AnalyzeStageResult()

    compiler.apply_syllabus_to_outline(
        outline,
        body=CourseFromArticleRequest(article="x" * 80, locale="ru"),
        article="x" * 80,
        chapters=[
            {
                "id": "t1",
                "title": "Redis в продакшене (1)",
                "objective": "Разобрать первый раздел",
                "source_excerpt": "Первая версия была написана на языке Tcl.",
            }
        ],
        outcomes=["Эксплуатация Redis"],
        source_title="Redis: устройство и эксплуатация",
    )

    assert outline.title == "Redis: устройство и эксплуатация"
    assert outline.pack_id == "redis"


@pytest.mark.asyncio
async def test_syllabus_stays_within_requested_course_depth(tmp_path: Path) -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    store_mod = load_service_module("app.domain.course_build.store")
    target_mod = load_service_module("app.domain.llm.target")
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "Docker"},
        title="Docker",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    topics = [
        "слои образа",
        "тома данных",
        "пользовательские сети",
        "реестр образов",
        "переменные окружения",
        "многоэтапная сборка",
        "проверка живости",
        "лимиты памяти",
        "журналы контейнера",
        "политика перезапуска",
        "секреты сборки",
        "теги и версии",
    ]
    sources = [
        {
            "title": f"Docker глазами практика {number}",
            "content": "\n\n".join(
                _docker_section(topic) for topic in topics[number * 4 : number * 4 + 4]
            ),
        }
        for number in range(3)
    ]
    dump = "\n\n".join(str(item["content"]) for item in sources)

    async def fake_order(*_args, **kwargs):
        return list(kwargs["seeds"]), ["Собрать образ и запустить контейнер"]

    with patch.object(compiler, "order_seeds_with_llm", new=fake_order):
        chapters, _outcomes = await compiler.compile_local_syllabus(
            AsyncMock(),
            target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
            body=CourseFromArticleRequest(article=dump, locale="ru", course_depth="light"),
            sources=sources,
            article=dump,
            policy=policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b"),
            store=store,
            user_id=user_id,
            build_id=build_id,
            warnings=[],
        )

    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    uncapped = collapse.fit_seed_count(
        inventory.inventory_from_sources(sources, article=dump, sentences_per_window=3),
        max_chapters=100,
    )

    assert len(uncapped) > 10
    assert 0 < len(chapters) <= 3
    assert all(item["source_excerpt"].strip() for item in chapters)


def test_chapter_ceiling_follows_corpus_volume() -> None:
    budget = load_service_module("app.domain.course_from_article.curriculum.outline.chapter_budget")
    body = CourseFromArticleRequest(
        article=_docker_section("тома данных"),
        locale="ru",
        course_depth="standard",
    )

    thin = budget.chapter_ceiling(body, corpus_chars=20_000, hard_max=100)
    rich = budget.chapter_ceiling(body, corpus_chars=200_000, hard_max=100)
    compact = budget.chapter_ceiling(body, corpus_chars=200_000, hard_max=8)

    prompt_dump = budget.chapter_ceiling(body, corpus_chars=48_000, hard_max=100)
    from_sources = budget.corpus_char_count(
        [{"content": "a" * 90_000}, {"content": "b" * 90_000}],
        article="x" * 48_000,
    )

    assert thin == 6
    assert rich == 12
    assert compact == 8
    assert prompt_dump == 6
    assert from_sources == 180_000
    assert budget.chapter_ceiling(body, corpus_chars=from_sources, hard_max=100) == 12


def test_chapter_ceiling_respects_explicit_theory_count() -> None:
    budget = load_service_module("app.domain.course_from_article.curriculum.outline.chapter_budget")
    body = CourseFromArticleRequest(
        article=_docker_section("слои образа"),
        locale="ru",
        course_depth="standard",
        theory_count=8,
    )

    assert budget.chapter_ceiling(body, corpus_chars=200_000, hard_max=100) == 8
    assert budget.chapter_ceiling(body, corpus_chars=5_000, hard_max=100) == 8


def test_relabel_rejects_sentence_fragment_title() -> None:
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    chapters = [
        {
            "id": "t1",
            "title": "Redis Sentinel",
            "objective": "Разобрать отказоустойчивость",
            "source_excerpt": "Sentinel отслеживает ведущий узел.",
        }
    ]

    relabeled = compiler._relabel_from_payload(
        chapters,
        [],
        {
            "chapters": [
                {
                    "id": "t1",
                    "title": "Также с помощью Redis можно",
                    "objective": "Настроить Sentinel",
                }
            ]
        },
    )

    assert relabeled is not None
    assert relabeled[0][0]["title"] == "Redis Sentinel"


def _long_form_source(marker: int, *, blocks: int, headings: bool) -> str:
    terms = [f"термин{marker}{index:02d}" for index in range(40)]
    paragraphs = []
    for block in range(blocks):
        window = terms[(block * 3) % 40 :] + terms[: (block * 3) % 40]
        prose = " ".join(
            f"Приём {' '.join(window[step * 3 : step * 3 + 9])} меняет поведение системы."
            for step in range(10)
        )
        paragraphs.append(f"## Раздел {window[0]} {window[1]}\n{prose}" if headings else prose)
    return "\n\n".join(paragraphs)


def _corpus(sources: int, *, blocks: int, headings: bool = True) -> list[dict[str, object]]:
    return [
        {
            "title": f"Асинхронный Python часть {index}",
            "content": _long_form_source(100 + index * 7, blocks=blocks, headings=headings),
        }
        for index in range(sources)
    ]


def _compiled_topic_count(sources: list[dict[str, object]], *, depth: CourseDepth) -> int:
    budget = load_service_module("app.domain.course_from_article.curriculum.outline.chapter_budget")
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    body = CourseFromArticleRequest(article="x" * 400, locale="ru", course_depth=depth)
    cap = budget.chapter_ceiling(
        body,
        corpus_chars=budget.corpus_char_count(sources, ""),
        hard_max=100,
    )
    seeds = inventory.inventory_from_sources(sources, article="", sentences_per_window=3)
    return len(collapse.prepare_corpus(seeds, max_chapters=cap))


def test_chapter_floor_follows_corpus_and_depth() -> None:
    budget = load_service_module("app.domain.course_from_article.curriculum.outline.chapter_budget")
    standard = CourseFromArticleRequest(article="x" * 400, locale="ru", course_depth="standard")
    deep = CourseFromArticleRequest(article="x" * 400, locale="ru", course_depth="deep")

    thin = budget.chapter_floor(standard, corpus_chars=5_000, ceiling=12)
    rich = budget.chapter_floor(standard, corpus_chars=140_000, ceiling=12)
    deeper = budget.chapter_floor(deep, corpus_chars=140_000, ceiling=18)

    assert thin == 1
    assert rich == 6
    assert deeper == 10
    assert budget.chapter_floor(deep, corpus_chars=140_000, ceiling=4) == 4


def test_topic_count_grows_with_corpus_volume() -> None:
    small = _compiled_topic_count(_corpus(2, blocks=6), depth="standard")
    large = _compiled_topic_count(_corpus(6, blocks=14), depth="standard")

    assert small >= 3
    assert large >= 8
    assert large > small


def test_topic_count_grows_with_requested_depth() -> None:
    sources = _corpus(6, blocks=14)

    light = _compiled_topic_count(sources, depth="light")
    deep = _compiled_topic_count(sources, depth="deep")

    assert deep > light
    assert deep >= 10


def test_headingless_windows_stay_separate_topics() -> None:
    sources = _corpus(6, blocks=14, headings=False)

    assert _compiled_topic_count(sources, depth="standard") >= 6


def test_collapse_merges_only_when_content_repeats() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    shared_title = "Асинхронный Python (2)"
    repeated = (
        "Событийный цикл выполняет корутины по очереди и переключается на ожидании ввода-вывода. "
        * 6
    )
    distinct = "Пул соединений ограничивает число запросов к базе и держит очередь ожидания. " * 6
    seeds = [
        inventory.TopicSeed(
            title="Асинхронный Python (1)",
            objective="Разобрать событийный цикл",
            excerpt=repeated,
            source_title="Асинхронный Python",
            order=0,
        ),
        inventory.TopicSeed(
            title=shared_title,
            objective="Повторить событийный цикл",
            excerpt=repeated,
            source_title="Асинхронный Python",
            order=1,
        ),
        inventory.TopicSeed(
            title="Асинхронный Python (3)",
            objective="Разобрать пулы соединений",
            excerpt=distinct,
            source_title="Асинхронный Python",
            order=2,
        ),
    ]

    kept = collapse.collapse_near_duplicates(seeds)

    assert len(kept) == 2
    assert "Пул соединений" in kept[-1].excerpt


def test_merge_semantic_groups_keeps_the_corpus_floor() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    seeds = [
        inventory.TopicSeed(
            title=f"Тема {index}",
            objective=f"Разобрать тему {index}",
            excerpt=f"Материал темы {index}. " * 20,
            source_title="Курс",
            order=index,
            from_heading=True,
        )
        for index in range(8)
    ]
    greedy = [["0", "1", "2", "3"], ["4", "5", "6", "7"]]

    assert len(collapse.merge_semantic_groups(seeds, list(seeds), greedy)) == 2
    assert len(collapse.merge_semantic_groups(seeds, list(seeds), greedy, min_topics=5)) == 5
    assert len(collapse.merge_semantic_groups(seeds, list(seeds), greedy, min_topics=6)) == 8


def test_reject_duplicate_titles_keeps_distinct_material() -> None:
    outline = load_service_module("app.domain.course_from_article.local_course.curriculum.outline")
    chapters = [
        {
            "id": "t1",
            "title": "Асинхронный Python (1)",
            "objective": "Разобрать событийный цикл",
            "source_excerpt": "Событийный цикл переключает корутины на вводе-выводе. " * 6,
        },
        {
            "id": "t2",
            "title": "Асинхронный Python (2)",
            "objective": "Разобрать пулы соединений",
            "source_excerpt": "Пул соединений держит очередь запросов к базе под нагрузкой. " * 6,
        },
    ]

    assert outline.reject_duplicate_titles(chapters) == chapters
    assert outline.chapter_titles_are_unique(chapters)


def test_shell_title_rejects_code_fragment_headings() -> None:
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )

    assert collapse.is_shell_title("Get the generator.")
    assert collapse.is_shell_title("return result")


def test_ensure_inventory_floor_keeps_one_topic_per_source() -> None:
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    collapse = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.collapse"
    )
    raw = [
        inventory.TopicSeed(
            title=f"Тема {index}",
            objective=f"Цель {index}",
            excerpt=f"Материал {index}. " * 40,
            source_title=f"Источник {index}",
            order=index,
            from_heading=True,
        )
        for index in range(5)
    ]
    collapsed = [raw[0], raw[1]]

    restored = collapse.ensure_inventory_floor(
        raw,
        collapsed,
        min_topics=4,
        max_chapters=10,
    )

    assert len(restored) >= 4
    assert len({seed.source_title for seed in restored}) >= 4
