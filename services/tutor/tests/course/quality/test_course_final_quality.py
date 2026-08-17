from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.domain.course_from_article.quality.final_quality import apply_final_course_quality


def test_cursor_final_quality_drops_duplicates_shell_chapter_and_saves_audit() -> None:
    chapters = [
        {
            "id": "storage",
            "title": "Хранение ключей",
            "objective": "Разобрать операции",
            "source_excerpt": "Redis хранит ключи и значения в памяти.",
        },
        {
            "id": "expiry",
            "title": "Срок жизни ключей",
            "objective": "Разобрать TTL",
            "source_excerpt": "TTL ограничивает срок жизни ключа.",
        },
        {
            "id": "summary",
            "title": "Заключение",
            "objective": "Подвести итог",
            "source_excerpt": "Краткий итог статьи.",
        },
    ]
    theory_steps: list[dict[str, object]] = [
        {
            "id": "theory-storage",
            "chapter_id": "storage",
            "content": "Redis хранит ключи и значения в памяти.",
        },
        {
            "id": "theory-expiry",
            "chapter_id": "expiry",
            "content": "Команда EXPIRE назначает ключу срок жизни.",
        },
        {
            "id": "theory-summary",
            "chapter_id": "summary",
            "content": "Повторим материал.",
        },
    ]
    choices = ["Команда EXPIRE", "Команда GET", "Команда PING", "Команда INFO"]
    quizzes: list[dict[str, object]] = [
        {
            "id": "quiz-storage",
            "chapter_id": "storage",
            "question": "Какая команда назначает ключу срок жизни?",
            "choices": choices,
            "answer": 0,
        },
        {
            "id": "quiz-expiry",
            "chapter_id": "expiry",
            "question": "Какая команда назначает ключу срок жизни?",
            "choices": choices,
            "answer": 0,
        },
        {
            "id": "quiz-summary",
            "chapter_id": "summary",
            "question": "Что завершает статью?",
            "choices": ["Итог", "TTL", "Ключ", "Значение"],
            "answer": 0,
        },
    ]
    warnings: list[str] = []
    store = MagicMock()

    apply_final_course_quality(
        chapters=chapters,
        theory_steps=theory_steps,
        quizzes=quizzes,
        practices=[],
        sources=[{"content": "Redis хранит ключи. TTL задаёт EXPIRE."}],
        strategy_pack="author-full",
        warnings=warnings,
        store=store,
        user_id=uuid4(),
        build_id=uuid4(),
    )

    assert [chapter["id"] for chapter in chapters] == ["storage", "expiry"]
    assert [quiz["id"] for quiz in quizzes] == ["quiz-storage"]
    assert all(step["chapter_id"] != "summary" for step in theory_steps)
    saved = store.save_blueprint.call_args.args[2]
    assert saved["quality_audit"]["level"] == "L1"
    assert "L2.visual_missing" in saved["quality_audit"]["must_fix"]
    assert saved["quality_audit"]["score"] < 100
    assert any("shell/invalid chapter" in warning for warning in warnings)
    assert any("near-duplicate quiz" in warning for warning in warnings)


def test_final_quality_cleans_near_duplicate_theory_after_polish() -> None:
    chapters = [
        {
            "id": "operations",
            "title": "Управление приложением",
            "objective": "Разобрать команды управления",
            "source_excerpt": "Команды запускают и останавливают приложение.",
        }
    ]
    detailed = (
        "Теперь рассмотрим команды для управления приложением, определенным в "
        "файле конфигурации. Команда `start` запускает все процессы из файла "
        "конфигурации. Команда `stop` останавливает и уничтожает все запущенные "
        "процессы. Для просмотра журналов запущенных процессов используется "
        "команда `logs`, а для отображения информации о текущем состоянии всех "
        "процессов — команда `status`."
    )
    repeated_lead = (
        "Теперь рассмотрим ключевые команды для управления приложением, "
        "определенным в файле конфигурации."
    )
    theory_steps: list[dict[str, object]] = [
        {
            "id": "theory-operations",
            "chapter_id": "operations",
            "kind": "theory",
            "content": f"{detailed}\n\n{repeated_lead}",
        }
    ]
    warnings: list[str] = []

    apply_final_course_quality(
        chapters=chapters,
        theory_steps=theory_steps,
        quizzes=[],
        practices=[],
        sources=[{"content": detailed}],
        strategy_pack="author-full",
        warnings=warnings,
        store=MagicMock(),
        user_id=uuid4(),
        build_id=uuid4(),
    )

    assert repeated_lead not in str(theory_steps[0]["content"])
    assert detailed in str(theory_steps[0]["content"])
    assert any("cleaned 1 theory chapter" in warning for warning in warnings)


def test_final_quality_drops_heading_only_theory_and_restores_mermaid() -> None:
    chapters = [
        {
            "id": "compare",
            "title": "Процессы против потоков",
            "objective": "Сравнить изоляцию",
            "source_excerpt": (
                "Поток разделяет память процесса, а отдельный процесс изолирует "
                "адресное пространство и не даёт сбою одного вычисления снести другое."
            ),
        }
    ]
    theory_steps: list[dict[str, object]] = [
        {
            "id": "theory-heading",
            "chapter_id": "compare",
            "kind": "theory",
            "title": "Процессы против потоков",
            "content": "# Процессы против потоков\n",
        },
        {
            "id": "theory-body",
            "kind": "theory",
            "title": "Процессы против потоков",
            "content": chapters[0]["source_excerpt"],
        },
    ]
    warnings: list[str] = []

    apply_final_course_quality(
        chapters=chapters,
        theory_steps=theory_steps,
        quizzes=[],
        practices=[],
        sources=[{"content": chapters[0]["source_excerpt"]}],
        strategy_pack="author-full",
        warnings=warnings,
        store=MagicMock(),
        user_id=uuid4(),
        build_id=uuid4(),
    )

    assert [step["id"] for step in theory_steps] == ["theory-body"]
    assert "```mermaid" in str(theory_steps[0]["content"])
    assert any("heading-only" in warning for warning in warnings)
