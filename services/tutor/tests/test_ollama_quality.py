from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_detects_arabic_and_cjk_in_prose() -> None:
    quality = load_service_module("app.domain.ollama_quality")
    dirty = "Мы знаем, что SELECT name вернет only names, а فقط homeworlds."
    assert quality.has_unexpected_scripts(dirty)
    assert not quality.has_unexpected_scripts("Используйте SELECT name, home_planet.")


def test_code_fences_do_not_trigger_script_check() -> None:
    quality = load_service_module("app.domain.ollama_quality")
    text = "Смотрите пример:\n```sql\nSELECT name FROM cadets;\n```\nДальше уточните цель."
    assert not quality.has_unexpected_scripts(text)


def test_infer_reply_language() -> None:
    quality = load_service_module("app.domain.ollama_quality")
    assert quality.infer_reply_language("Почему нужен JOIN?") == "ru"
    assert quality.infer_reply_language("Why do I need a JOIN here?") == "en"


def test_pick_better_reply_keeps_clean_draft() -> None:
    quality = load_service_module("app.domain.ollama_quality")
    draft = "Сначала выберите нужные столбцы через SELECT name, home_planet."
    polished = "Сначала выберите столбцы: فقط names and planets."
    assert quality.pick_better_reply(draft, polished, language="ru") == draft


def test_language_mismatch_for_russian_prose() -> None:
    quality = load_service_module("app.domain.ollama_quality")
    english_wall = (
        "First you should think about projection. "
        "Then list the columns you need from cadets and write a SELECT. "
        "Finally check the result against the task statement carefully."
    )
    assert quality.language_mismatch(english_wall, "ru")
    assert not quality.language_mismatch(
        "Сначала подумайте о проекции столбцов, затем напишите SELECT name, home_planet.",
        "ru",
    )
