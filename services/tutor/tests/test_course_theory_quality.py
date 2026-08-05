from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_strip_throat_clearing_removes_filler_intro() -> None:
    dedupe = load_service_module("app.domain.llm.prose_dedupe")
    raw = (
        "В этой главе мы рассмотрим дескрипторы и их роль в валидации.\n\n"
        "Дескриптор — объект с методами `__get__` и `__set__`.\n"
    )
    cleaned = dedupe.strip_throat_clearing(raw)
    assert "В этой главе" not in cleaned
    assert "Дескриптор" in cleaned


def test_collapse_exact_repeated_lesson_block() -> None:
    dedupe = load_service_module("app.domain.llm.prose_dedupe")
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
    dedupe = load_service_module("app.domain.llm.prose_dedupe")
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
    quality = load_service_module("app.domain.ollama_quality")
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


def test_vidaenii_typo_triggers_retry() -> None:
    quality = load_service_module("app.domain.ollama_quality")
    dirty = (
        "Какие определения лучше описывают данные в компьютерном видаении "
        "и почему нельзя верить одному кадру без правил системы вокруг модели."
    )
    assert quality.needs_quality_retry(dirty, "ru")
