from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_strip_throat_clearing_removes_filler_intro() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = (
        "В этой главе мы рассмотрим дескрипторы и их роль в валидации.\n\n"
        "Дескриптор — объект с методами `__get__` и `__set__`.\n"
    )
    cleaned = dedupe.strip_throat_clearing(raw)
    assert "В этой главе" not in cleaned
    assert "Дескриптор" in cleaned


def test_collapse_exact_repeated_lesson_block() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    block = (
        "Введение в компьютерное зрение\n"
        "Ментальный образ\n"
        "Компьютерное зрение превращает кадры в структурированные данные: "
        "классы, координаты, маски и события. Модель даёт сигнал, решение — правила.\n"
        "Пример\n"
        "Камера на улице находит людей и машины на каждом кадре.\n"
        "Краткое повторение\n"
        "CV превращает пиксели в полезные факты для системы.\n"
    )
    looped = (block + "\n") * 5
    cleaned = dedupe.collapse_repeated_prose(looped)
    assert cleaned.count("Ментальный образ") == 1
    assert "Камера на улице" in cleaned
    assert len(cleaned) < len(looped) // 2


def test_continuation_restart_detected() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    assembled = (
        "Введение в компьютерное зрение\n"
        "Ментальный образ\n"
        "Компьютерное зрение превращает кадры в данные.\n"
    )
    restart = assembled + "Ещё раз то же самое с самого начала.\n"
    assert dedupe.continuation_is_restart(assembled, restart)
    assert not dedupe.continuation_is_restart(
        assembled,
        "Дополнение: порог уверенности отсекает ложные срабатывания.\n",
    )


def test_script_mixing_triggers_quality_retry() -> None:
    quality = load_service_module("app.domain.ollama.quality")
    dirty = (
        "Комputer vision — это область, где изображения преобразуются "
        "в структурированные данные для систем безопасности и анализа."
    )
    assert quality.has_script_mixing(dirty)
    assert quality.needs_quality_retry(dirty, "ru")
    clean = (
        "Компьютерное зрение — это область, где изображения преобразуются "
        "в структурированные данные для систем безопасности и анализа."
    )
    assert not quality.has_script_mixing(clean)
    assert not quality.needs_quality_retry(clean, "ru")


def test_repair_script_mixing_fixes_docker_glitch() -> None:
    quality = load_service_module("app.domain.ollama.quality_lang")
    dirty = "Дocker решает эту проблему через контейнеры и образы."
    repaired = quality.repair_script_mixing(dirty)
    assert "Дocker" not in repaired
    assert "Docker" in repaired
    assert not quality.has_script_mixing(repaired)
    assert not quality.needs_quality_retry(repaired, "ru")


def test_theory_windows_are_capped() -> None:
    theory = load_service_module("app.domain.course_from_article.local_course.content.theory")
    excerpt = " ".join(f"Предложение номер {index} про контейнеры Docker." for index in range(40))
    windows = theory._windows_for_chapter(
        {"title": "Что такое Docker?", "source_excerpt": excerpt},
        sentences_per_window=3,
    )
    assert 1 <= len(windows) <= 8
    assert sum(len(window) for window in windows) >= len(excerpt) // 2


def test_vidaenii_typo_triggers_retry() -> None:
    quality = load_service_module("app.domain.ollama.quality")
    dirty = (
        "Какие определения лучше описывают данные в компьютерном видаении "
        "и почему нельзя верить одному кадру без правил системы вокруг модели."
    )
    assert quality.needs_quality_retry(dirty, "ru")


def test_collapse_repeated_sections_drops_duplicate_headings() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = (
        "## Структурирование кода\n"
        "Первый блок про модули.\n\n"
        "## Заключение\n"
        "Короткий мостик.\n\n"
        "## Структурирование кода\n"
        "Повтор того же блока.\n\n"
        "## Заключение\n"
        "Ещё раз заключение.\n"
    )
    cleaned = dedupe.collapse_repeated_sections(raw)
    assert cleaned.count("## Структурирование кода") == 1
    assert cleaned.count("## Заключение") == 1
    assert "Повтор того же блока" not in cleaned


def test_collapse_similar_paragraphs_drops_stutter_openings() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = "\n\n".join(
        [
            "## Зачем это нужно?",
            "Разделение моделей по файлам упрощает чтение и сопровождение кода проекта.",
            "Разделение моделей по файлам помогает держать слои приложения изолированными.",
            "Разделение моделей по файлам позволяет избежать циклических импортов в пакетах.",
            "Отдельно: используйте `TYPE_CHECKING` для аннотаций.",
        ]
    )
    cleaned = dedupe.collapse_similar_paragraphs(raw)
    assert cleaned.count("Разделение моделей по файлам") == 1
    assert "TYPE_CHECKING" in cleaned


def test_collapse_similar_paragraphs_keeps_nonadjacent_shared_openings() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = "\n\n".join(
        [
            "## One",
            "В этой главе мы разберём маршрутизацию запросов и балансировку.",
            "Дальше про кэш и TTL.",
            "## Two",
            "В этой главе мы разберём очереди сообщений и подтверждения.",
        ]
    )
    cleaned = dedupe.collapse_similar_paragraphs(raw)
    assert cleaned.count("В этой главе мы разберём") == 2


def test_clean_theory_drops_rephrased_loops_and_navigation() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = "\n\n".join(
        [
            (
                "Команда `docker run -d -p 8080:80 nginx` запускает Nginx в фоне "
                "и публикует порт 80 контейнера на порту 8080 хоста."
            ),
            (
                "Флаг `-d` запускает Nginx в фоновом режиме, а `-p 8080:80` "
                "публикует порт 80 контейнера через порт 8080 хоста."
            ),
            "В следующем разделе мы поговорим о Docker Compose.",
            (
                "Команда `docker ps` показывает идентификатор, образ и текущее "
                "состояние каждого запущенного контейнера."
            ),
        ]
    )

    cleaned = dedupe.clean_theory_markdown(raw)

    assert cleaned.count("8080") == 2
    assert "следующем разделе" not in cleaned
    assert "docker ps" in cleaned


def test_clean_theory_strips_inline_and_orphan_code_blobs() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = (
        "Теперь давай запустим эту функцию и посмотрим, что произойдет: "
        "```python\ndef test_function_two(listing=None) -> None:\n"
        "    if listing is None:\n        listing = []\n```\n\n"
        "a = [1, 2.2, 'python']\n"
        'print("a[2] =", a[2])\n\n'
        "Изменяемые аргументы по умолчанию сохраняют состояние между вызовами.\n\n"
        "Схема потока:\n\n"
        "```mermaid\nflowchart TD\n    A[Start] --> B[Work]\n```\n"
    )
    cleaned = dedupe.clean_theory_markdown(raw)
    assert "test_function_two" not in cleaned
    assert "a[2]" not in cleaned
    assert "Изменяемые аргументы" in cleaned
    assert "```mermaid" in cleaned
    assert "flowchart TD" in cleaned


def test_clean_theory_strips_resource_link_dump_paragraphs() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = (
        "Контейнер изолирует процесс через namespaces и cgroups.\n\n"
        "- [Установите Docker](https://docs.example.com/install) "
        "- [Начните работу](https://docs.example.com/start)\n\n"
        "1. [Установите Desktop](https://docs.example.com/desktop)\n\n"
        "Образы собираются из слоёв файловой системы."
    )
    cleaned = dedupe.clean_theory_markdown(raw)
    assert "namespaces" in cleaned
    assert "слоёв" in cleaned
    assert "Установите Docker" not in cleaned
    assert "Установите Desktop" not in cleaned
    assert "docs.example.com" not in cleaned


def test_clean_theory_markdown_combines_dedupe_passes() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = (
        "В этой главе мы рассмотрим модули.\n\n"
        "## Структурирование кода\n"
        "Первый блок.\n\n"
        "## Структурирование кода\n"
        "Дубль.\n"
    )
    cleaned = dedupe.clean_theory_markdown(raw)
    assert "В этой главе" not in cleaned
    assert cleaned.count("## Структурирование кода") == 1
    assert "Дубль" not in cleaned


def test_collapse_heading_cycle_kills_alternating_ab_loop() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = "\n\n".join(
        [
            "## Разделение кода и структурирование проекта",
            "a" * 100,
            "## 2. Использование Dependency Injection",
            "b" * 100,
            "## Разделение кода и структурирование проекта",
            "c" * 100,
            "## 2. Использование Dependency Injection",
            "d" * 100,
            "## Разделение кода и структурирование проекта",
            "e" * 100,
            "## 2. Использование Dependency Injection",
            "f" * 100,
        ]
    )
    cleaned = dedupe.clean_theory_markdown(raw)
    assert cleaned.count("## Разделение кода") == 1
    assert cleaned.count("Dependency Injection") == 1
    assert "c" * 20 not in cleaned


def test_split_after_loop_yields_few_unique_titles() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = "\n\n".join(
        [
            "## Разделение кода и структурирование проекта",
            "a" * 2000,
            "## 2. Использование Dependency Injection",
            "b" * 2000,
            "## Разделение кода и структурирование проекта",
            "c" * 2000,
            "## 2. Использование Dependency Injection",
            "d" * 2000,
            "## Структурирование кода в FastAPI и SQLAlchemy",
            "e" * 2000,
            "## Разделение кода и структурирование проекта",
            "f" * 2000,
        ]
    )
    cleaned = dedupe.clean_theory_markdown(raw)
    steps = split_mod.split_long_theory_steps(
        [{"id": "t1", "kind": "theory", "title": "Модули", "content": cleaned}],
        enabled=True,
        max_chars=1200,
        max_parts=6,
    )
    titles = [str(item["title"]) for item in steps]
    assert len(steps) <= 3
    assert len(set(titles)) == len(titles)
    assert not any(title.startswith("2.") for title in titles)


def test_theory_prose_prompt_includes_instructional_skills() -> None:
    facade = load_service_module("app.domain.prompt_compose.facade")
    prompt = facade.course_from_article_theory_prose_prompt(compact=False)
    assert "One chapter = one idea" in prompt
    assert "plain markdown only" in prompt.casefold()
    assert "Output **JSON only**" in prompt
    assert "Override any JSON-only instruction" in prompt
    assert prompt.casefold().find("plain markdown only") < prompt.find("Output **JSON only**")


def test_dedupe_theory_steps_across_course_keeps_first_long_sentence() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    repeated = (
        "Но если данные отсутствуют в кэше (промах), то приложение получает "
        "данные из основной базы и записывает их в кэш."
    )
    steps = [
        {
            "kind": "theory",
            "title": "Кэш 1",
            "content": f"Redis ускоряет чтение. {repeated} TTL задаёт срок жизни.",
        },
        {
            "kind": "theory",
            "title": "Кэш 2",
            "content": f"Кэш рядом с базой. {repeated} Инвалидация остаётся за приложением.",
        },
    ]
    touched = dedupe.dedupe_theory_steps_across_course(steps)
    assert touched == 1
    assert repeated in str(steps[0]["content"])
    assert repeated not in str(steps[1]["content"])
    assert "Инвалидация" in str(steps[1]["content"])


def test_strip_navigation_heading_and_sentence() -> None:
    dedupe = load_service_module("app.domain.llm.content.prose_dedupe")
    raw = (
        "## Переход к следующему разделу\n\n"
        "Docker daemon принимает API-запросы.\n\n"
        "В следующем разделе мы разберём образы подробнее.\n\n"
        "Контейнер изолирует процесс через namespaces."
    )
    cleaned = dedupe.clean_theory_markdown(raw)
    assert "Переход к следующему" not in cleaned
    assert "В следующем разделе" not in cleaned
    assert "Docker daemon" in cleaned
    assert "namespaces" in cleaned


def test_split_skips_navigation_part_title() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    body = "\n\n".join(
        [
            "## Архитектура Docker: как он устроен и как работает",
            "a" * 1200,
            "## Далее - Архитектура Docker: как он устроен и как работает.",
            "b" * 1200,
        ]
    )
    split = split_mod.split_long_theory_steps(
        [{"id": "t1", "kind": "theory", "title": "Архитектура Docker", "content": body}],
        enabled=True,
        max_chars=1000,
        max_parts=3,
    )
    titles = [str(item["title"]) for item in split]
    assert not any(title.casefold().startswith("далее") for title in titles)
    assert not any("переход" in title.casefold() for title in titles)


def test_split_absorbs_heading_only_first_part() -> None:
    split_mod = load_service_module("app.domain.course_from_article.curriculum.theory.theory_split")
    body = "\n\n".join(
        [
            "# Платформа",
            "## Что такое платформа",
            "a" * 900,
            "## Как устроены слои",
            "b" * 900,
        ]
    )
    split = split_mod.split_long_theory_steps(
        [{"id": "t1", "kind": "theory", "title": "Платформа", "content": body}],
        enabled=True,
        max_chars=800,
        max_parts=3,
    )
    bodies = [str(item["content"]) for item in split]
    assert all(len(body) >= 420 for body in bodies)
    assert not any(body.strip() == "# Платформа" for body in bodies)
    assert any("Что такое платформа" in body or "слои" in body for body in bodies)
