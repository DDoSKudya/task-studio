from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from studio_contracts.api.studio_schemas import CourseFromArticleRequest
from tutor_helpers.loaders import load_service_module


def test_quiz_prompt_includes_article_seeds() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    prompt = messages.quiz_user_message(
        locale="ru",
        chunk=2,
        title="Routers",
        objective="Split routers",
        theory="APIRouter groups related HTTP routes.",
        already=[],
        article_seeds="### [quiz] Check routers\nWhat does APIRouter group?",
    )
    assert "Article checks to adapt into the course locale" in prompt
    assert "Check routers" in prompt
    spaced = messages.quiz_user_message(
        locale="ru",
        chunk=2,
        title="Sessions",
        objective="Bind the session",
        theory="Session is a desk.",
        already=[],
        prior_digest="APIRouter groups related HTTP routes.",
    )
    assert "earlier idea" in spaced.casefold() or "earlier chapter" in spaced.casefold()
    assert "APIRouter" in spaced
    assert '"question"' in prompt
    assert '"choices"' in prompt


def test_quiz_from_item_accepts_options_letter_and_dict_choices() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    schemas = load_service_module("app.domain.course_from_article.local_course.policy.schemas")
    lettered = loop._quiz_from_item(
        {
            "stem": "When should you expose OpenAPI from FastAPI?",
            "options": [
                "When the API is the product",
                "When you need a desktop GUI",
                "When you only serve static HTML",
                "When you replace PostgreSQL",
            ],
            "answer": "B",
        },
        topic_key="t1",
        index=1,
    )
    assert lettered is not None
    assert lettered["answer"] == 1
    assert len(lettered["choices"]) == 4
    mapped = loop._quiz_from_item(
        {
            "q": "Why pick FastAPI for async handlers?",
            "choices": {
                "A": "Native async and type hints",
                "B": "Built-in PHP templates",
                "C": "Replaces the database",
                "D": "No HTTP at all",
            },
            "correct": "A",
        },
        topic_key="t1",
        index=2,
    )
    assert mapped is not None
    assert mapped["answer"] == 0
    nested = loop._quiz_from_item(
        {
            "quiz": {
                "question": "What does APIRouter group in FastAPI?",
                "choices": ["Related HTTP routes", "SQL tables", "CSS files", "GPU kernels"],
                "answer": 0,
            }
        },
        topic_key="t1",
        index=3,
    )
    assert nested is not None
    assert "APIRouter" in str(nested["question"])
    husk = loop._quiz_from_item({}, topic_key="t1", index=4)
    assert husk is None
    items = schemas.payload_items(
        {
            "question": "When should you pick FastAPI over Flask?",
            "choices": ["Need async OpenAPI", "Need PHP", "Need a GUI", "Need COBOL"],
            "answer": 0,
        },
        plural="quizzes",
        singular="quiz",
    )
    assert len(items) == 1
    empty_batch = schemas.payload_items(
        {"quizzes": [{}]},
        plural="quizzes",
        singular="quiz",
    )
    assert empty_batch == [{}]
    assert loop._quiz_from_item({}, topic_key="t1", index=5) is None


def test_quiz_from_item_strips_choices_duplicated_in_stem() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    strategies = load_service_module("app.domain.course_strategies")
    choices = [
        "Удалённый сервер словарей, который хранит непрозрачные блобы",
        "Кэш для ускорения доступа к данным в базе",
        "Сервер структур данных, который также работает как кэш",
        "Простое хранилище ключей с ограниченными возможностями",
    ]
    quiz = loop._quiz_from_item(
        {
            "question": "Какое определение Redis точнее?\n\n"
            + "\n".join(f"{letter}) {text}" for letter, text in zip("ABCD", choices, strict=True)),
            "choices": choices,
            "answer": "C",
        },
        topic_key="t1",
        index=1,
    )
    assert quiz is not None
    assert quiz["question"] == "Какое определение Redis точнее?"
    assert quiz["choices"] == choices
    assert quiz["answer"] == 2
    same_stem = strategies.quiz_stem_key("Какое определение Redis точнее?")
    assert strategies.quiz_stem_key(str(quiz["question"])) == same_stem


def test_quiz_from_item_recovers_inline_abcd_choices() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    recovered = loop._quiz_from_item(
        {
            "question": (
                "FastAPI использует библиотеку Pydantic для чего?\n"
                "A) Обеспечения безопасности API\n"
                "B) Валидации данных по type hints\n"
                "C) Замены PostgreSQL\n"
                "D) Рисования GUI"
            ),
            "answer": "B",
        },
        topic_key="t1",
        index=1,
    )
    assert recovered is not None
    assert "choices" in recovered
    assert len(recovered["choices"]) == 4
    assert recovered["answer"] == 1
    assert "A)" not in str(recovered["question"])
    assert all(
        not str(choice).startswith(("A)", "B)", "C)", "D)")) for choice in recovered["choices"]
    )
    assert "Pydantic" in str(recovered["question"])


def test_quiz_from_item_completes_three_choices_from_correct_answer() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")

    quiz = loop._quiz_from_item(
        {
            "question": "Что запускает автоматическое переключение Redis Sentinel?",
            "choices": [
                "Кворум наблюдателей",
                "Команда GET клиента",
                "Истечение TTL любого ключа",
            ],
            "answer": 0,
        },
        topic_key="t1",
        index=1,
    )

    assert quiz is not None
    assert quiz["answer"] == 0
    assert len(quiz["choices"]) == 4
    assert "Кворум наблюдателей" in str(quiz["choices"][3])
    assert quiz["choices"][3] != quiz["choices"][0]


@pytest.mark.asyncio
async def test_compiled_quiz_stem_is_not_sent_back_to_llm() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    captured: list[str] = []

    async def fake_chunk(*_args, **kwargs):
        captured.extend(kwargs["already_questions"])
        return [
            {
                "id": "t1-quiz-2",
                "kind": "quiz",
                "title": "Sentinel: кворум",
                "question": "Как кворум Sentinel влияет на автоматическое переключение?",
                "choices": [
                    "Запускает согласованное переключение",
                    "Удаляет все ключи",
                    "Меняет TTL",
                    "Отключает реплики",
                ],
                "answer": 0,
            }
        ]

    compiled_stem = "Какое следствие для Sentinel следует из утверждения главы?"
    existing = {
        "id": "t1-quiz-g1",
        "kind": "quiz",
        "title": "Sentinel: роль в главе",
        "question": compiled_stem,
        "choices": [
            "Sentinel отслеживает ведущий узел",
            "Sentinel заменяет все ключи",
            "Sentinel отключает сеть",
            "Sentinel удаляет реплики",
        ],
        "answer": 0,
    }
    theory = {
        "content": (
            "Redis Sentinel отслеживает ведущий узел. "
            "Кворум Sentinel запускает автоматическое переключение."
        )
    }
    with patch.object(loop, "_quiz_chunk", new=fake_chunk):
        quizzes = await loop.generate_topic_quizzes(
            AsyncMock(),
            target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
            body=SimpleNamespace(locale="ru", include_quizzes=True),
            chapter={"title": "Redis Sentinel", "objective": "Настроить переключение"},
            theory=theory,
            count=2,
            policy=policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b"),
            topic_key="t1",
            warnings=[],
            already=[existing],
        )

    assert len(quizzes) == 2
    assert compiled_stem not in captured


def test_practice_from_item_accepts_brief_aliases() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    task = loop._practice_from_item(
        {
            "name": "Роутер пользователей",
            "brief": (
                "Дано: модуль users. Допиши include_router так, "
                "чтобы эндпоинты пользователей отвечали. "
                "Ожидаемый результат: рабочий router без GUI."
            ),
            "starter_code": (
                "from fastapi import APIRouter\n\nrouter = APIRouter()\n\n# TODO: добавь маршрут\n"
            ),
        },
        topic_key="t1",
        index=1,
        theory="APIRouter groups related HTTP routes in FastAPI packages.",
    )
    assert task is not None
    assert task["title"]
    assert "Дано" in str(task["content"])
    assert "APIRouter" in str(task["template"])
    assert "NotImplementedError" not in str(task["template"])


def test_practice_from_item_normalizes_chapter_alias_fence_and_runtime() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")

    task = loop._practice_from_item(
        {
            "chapter": "Настрой репликацию Redis",
            "content": (
                "Допиши команду настройки реплики и объясни, как она связывается с ведущим узлом."
            ),
            "template": "```shell\nredis-cli REPLICAOF TODO\n```",
        },
        topic_key="t1",
        index=1,
        theory="Команда REPLICAOF связывает реплику с ведущим узлом.",
        fallback_runtime="shell",
    )

    assert task is not None
    assert task["title"] == "Настрой репликацию Redis"
    assert task["runtime"] == "shell"
    assert "```" not in str(task["template"])


def test_practice_from_item_joins_list_template() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    task = loop._practice_from_item(
        {
            "title": "Продюсер Kafka",
            "content": "Допиши отправку сообщения в топик email_notifications без GUI.",
            "template": [
                "from kafka import KafkaProducer",
                "producer = KafkaProducer(bootstrap_servers='localhost:9092')",
                "# TODO: send",
            ],
        },
        topic_key="t1",
        index=2,
        theory="Producer sends records into a Kafka topic.",
    )
    assert task is not None
    template = str(task["template"])
    assert "KafkaProducer" in template
    assert "\n" in template
    assert not template.strip().startswith("[")


def test_practice_from_item_prefers_requested_runtime_over_detected_code() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")

    task = loop._practice_from_item(
        {
            "title": "Настрой драйвер логирования",
            "content": "Допиши команду Docker для запуска контейнера с драйвером journald.",
            "template": "package main\n\nfunc main() {\n    // TODO\n}\n",
        },
        topic_key="t1",
        index=1,
        theory="Docker также написан на Go, но управляется командами Docker CLI.",
        fallback_runtime="bash",
    )

    assert task is not None
    assert task["runtime"] == "bash"


def test_meta_fallback_quiz_markers_are_rejected() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    theory = "Kafka topic stores messages; producer writes, consumer reads."
    patterns = (
        "Когда в этой главе уместен Kafka, а не сбор всего в одном месте?",
        "Что сломается в шаге главы, если обойти Apache и оставить как было?",
        "Чем Topic в этой главе отличается от решения «потом разберёмся»?",
    )
    for question in patterns:
        bad = {
            "kind": "quiz",
            "title": "Kafka: проверка шага",
            "question": question,
            "choices": [
                "Применить Kafka так, как разобрано в тексте главы",
                "Свести главу к заголовку и не менять структуру",
                "Заменить этот шаг проверкой орфографии в комментариях",
                "Вынести решение в отдельный графический интерфейс",
            ],
            "answer": 0,
        }
        assert heuristics.quiz_looks_like_template(bad) is True
        assert heuristics.quiz_item_is_usable(bad, theory=theory, locale="ru") is False


def test_repeated_quiz_stems_drop_narrow_rephrasing() -> None:
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    quizzes = [
        {
            "question": "Какой драйвер логирования используется по умолчанию в Docker?",
        },
        {
            "question": (
                "Какой драйвер логирования используется по умолчанию в Docker "
                "для записи логов в файлы JSON?"
            ),
        },
    ]

    kept = loop._drop_repeated_stems(quizzes, seen=[])

    assert len(kept) == 1


def test_quiz_rejects_answer_index_that_contradicts_theory_sentence() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    theory = (
        "По умолчанию Docker сохраняет логи через драйвер json-file. "
        "Драйвер journald записывает логи в системный журнал Linux. "
        "Драйвер syslog отправляет логи на внешний сервер, а fluentd собирает их "
        "для последующей обработки."
    )
    quiz = {
        "question": "Какой драйвер записывает логи в системный журнал Linux?",
        "choices": ["json-file", "journald", "syslog", "fluentd"],
        "answer": 2,
    }

    assert heuristics.quiz_answer_matches_theory_context(quiz, theory) is False
    assert heuristics.quiz_item_is_usable(quiz, theory=theory, locale="ru") is False

    quiz["answer"] = 1
    assert heuristics.quiz_answer_matches_theory_context(quiz, theory) is True


def test_practice_prompt_includes_article_seeds() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    prompt = messages.practice_user_message(
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        chunk=1,
        title="Routers",
        objective="Split routers",
        theory="APIRouter groups related HTTP routes.",
        already=[],
        article_seeds="### [practice] Router lab\nGiven a package, Expected a router.",
    )
    assert "Article labs to adapt into the course locale" in prompt
    assert "Router lab" in prompt
    assert "закрепление" in prompt
    assert "Дано:" in prompt
    assert "не обязательны" in prompt.casefold()
    assert "completion problem" in prompt.casefold() or "worked example" in prompt.casefold()


def test_quiz_prompt_uses_bloom_band_by_chapter_index() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    early = messages.quiz_user_message(
        locale="ru",
        chunk=1,
        title="Terms",
        objective="Назвать topic и partition",
        theory="Topic stores messages in partitions.",
        already=[],
        chapter_index=0,
        chapter_total=10,
    )
    late = messages.quiz_user_message(
        locale="ru",
        chunk=1,
        title="Trade-offs",
        objective="Выбрать semantics доставки",
        theory="At-least-once may duplicate; exactly-once needs idempotent producer.",
        already=[],
        prior_digest="Topic stores messages.",
        chapter_index=9,
        chapter_total=10,
    )
    assert "Bloom band: early" in early
    assert "Bloom band: late" in late
    assert "Earlier chapter residue" in late


def test_polish_title_and_measurable_objective() -> None:
    outline = load_service_module("app.domain.course_from_article.local_course.curriculum.outline")
    assert outline.polish_chapter_title("№3 BEST-PRACTICES В РАБОТЕ С KAFKA") == (
        "Best-practices в работе с kafka"
    )
    obj = outline.ensure_measurable_objective(
        "Топики",
        "понять топики",
        locale="ru",
    )
    assert "уметь" in obj.casefold()
    assert "Топики" in obj


def test_stamp_chapter_id_keeps_quizzes_in_own_topic() -> None:
    runner = load_service_module("app.domain.course_from_article.local_course.runtime.runner")
    quizzes = [
        {"id": f"q-{index}", "kind": "quiz", "title": f"Q{index}", "question": "?"}
        for index in range(1, 5)
    ]
    runner._stamp_chapter_id(quizzes[:2], "intro")
    runner._stamp_chapter_id(quizzes[2:], "advanced")
    assemble = load_service_module("app.domain.course_from_article.pack.assemble_manifest")
    manifest = assemble._assemble_interleaved_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        chapters=[
            {"id": "intro", "title": "Intro"},
            {"id": "advanced", "title": "Advanced"},
        ],
        theory_steps=[
            {
                "id": "theory-intro",
                "kind": "theory",
                "title": "Intro",
                "content": "x",
                "chapter_id": "intro",
            },
            {
                "id": "theory-advanced",
                "kind": "theory",
                "title": "Advanced",
                "content": "y",
                "chapter_id": "advanced",
            },
        ],
        quiz_steps=quizzes,
        code_steps=[],
    )
    topics = manifest["topics"]
    assert topics[0]["phases"]["assess"]["steps"] == ["q-1", "q-2"]
    assert topics[1]["phases"]["assess"]["steps"] == ["q-3", "q-4"]


def test_reject_duplicate_titles_does_not_suffix() -> None:
    outline = load_service_module("app.domain.course_from_article.local_course.curriculum.outline")
    chapters = [
        {
            "id": "a",
            "title": "Introduction to FastAPI and Minimal API Example",
            "objective": "intro",
            "source_excerpt": "one",
        },
        {
            "id": "b",
            "title": "Introduction to FastAPI and Minimal API Example",
            "objective": "intro again",
            "source_excerpt": "two",
        },
        {
            "id": "c",
            "title": "Dependency Injection with Depends",
            "objective": "di",
            "source_excerpt": "three",
        },
    ]
    kept = outline.reject_duplicate_titles(chapters)
    assert len(kept) == 2
    assert all("(2)" not in item["title"] for item in kept)
    assert outline.chapter_titles_are_unique(kept)


def test_local_quiz_practice_keep_full_token_budget() -> None:
    import inspect

    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    theory = load_service_module("app.domain.course_from_article.local_course.content.theory")
    source = inspect.getsource(loop) + inspect.getsource(theory)
    assert "min(policy.quiz_max_tokens" not in source
    assert "min(policy.practice_max_tokens" not in source
    assert "max_tokens=1800" not in source


def test_local_policy_preserves_volume_for_3b_and_7b() -> None:
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    three = policy_mod.local_course_policy_for(profile="cpu-light", model="qwen2.5:3b")
    seven = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    assert three.max_chapters == seven.max_chapters
    assert three.theory_max_tokens == seven.theory_max_tokens
    assert three.run_polish is seven.run_polish is True
    assert three.quality_rounds == seven.quality_rounds == 2
    assert three.section_quality_rounds == seven.section_quality_rounds == 2
    assert three.sentences_per_window == 1
    assert seven.sentences_per_window == 3
    cpu_seven = policy_mod.local_course_policy_for(profile="cpu-light", model="qwen2.5:7b")
    assert cpu_seven.sentences_per_window == 2
    assert three.quiz_batch_size == 1
    assert cpu_seven.quiz_batch_size == 1
    assert seven.quiz_batch_size == 1
    assert seven.practice_batch_size == 1


def test_apply_local_scale_never_changes_author_volume() -> None:
    runner = load_service_module("app.domain.course_from_article.local_course.runtime.runner")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    body = CourseFromArticleRequest(
        article="x" * 200,
        theory_count=40,
        quiz_count=8,
        practice_count=4,
        include_theory=True,
        include_quizzes=True,
        include_code=True,
    )
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    scaled = runner.apply_local_scale(body, policy)
    assert scaled.effective_theory_count() == 40
    assert scaled.effective_quiz_count() == 8
    assert scaled.effective_practice_count() == 4
    cpu = policy_mod.local_course_policy_for(profile="cpu-light", model="qwen2.5:3b")
    assert runner.apply_local_scale(body, cpu) == body


def test_requested_assess_counts_follow_author_toggles() -> None:
    runner = load_service_module("app.domain.course_from_article.local_course.runtime.runner")
    both = CourseFromArticleRequest(
        article="x" * 200,
        quiz_count=6,
        practice_count=3,
        include_quizzes=True,
        include_code=True,
    )
    none = CourseFromArticleRequest(
        article="x" * 200,
        quiz_count=6,
        practice_count=3,
        include_quizzes=False,
        include_code=False,
    )
    quizzes_only = CourseFromArticleRequest(
        article="x" * 200,
        quiz_count=4,
        practice_count=3,
        include_quizzes=True,
        include_code=False,
    )
    assert runner.requested_assess_counts(both) == (6, 3)
    assert runner.requested_assess_counts(none) == (0, 0)
    assert runner.requested_assess_counts(quizzes_only) == (4, 0)


def test_local_policy_runs_3b_with_more_smaller_requests_and_blocks_below() -> None:
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    assert policy_mod.model_meets_course_minimum("qwen2.5:3b") is True
    cpu = policy_mod.local_course_policy_for(profile="cpu-light", model="qwen2.5:3b")
    assert cpu.strategy_pack == "author-full"
    assert cpu.sentences_per_window == 1
    assert cpu.theory_max_continues == 1
    assert cpu.topic_retries == 6
    assert cpu.stage_retries == 4
    assert "strategy=cpu" in (cpu.warning or "")
    blocked = policy_mod.local_course_policy_for(profile="gpu-balanced", model="qwen2.5:1.5b")
    assert blocked.strategy_pack == "blocked"


def test_course_minimum_accepts_other_families_and_tiers_by_size() -> None:
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    select = load_service_module("app.domain.ollama.model_select")
    for name in (
        "llama3.1:8b",
        "llama3.1:8b-instruct-q4_K_M",
        "gemma2:9b",
        "mistral:7b",
        "qwen2.5:13b",
        "gemma2:3b",
    ):
        assert policy_mod.model_meets_course_minimum(name) is True, name
        assert select.model_is_course_capable(name) is True, name
    assert policy_mod.model_meets_course_minimum("qwen2.5:1.5b") is False
    assert select.course_model_tier("qwen2.5:1.5b") is None
    assert select.course_model_tier("gemma2:3b") == "cpu"
    assert select.course_model_tier("llama3.1:8b") == "standard"
    seven = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    assert seven.topic_retries == 4
    assert seven.stage_retries == 2


def test_template_quizzes_from_objective() -> None:
    fallbacks = load_service_module("app.domain.course_from_article.local_course.content.fallbacks")
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    theory = "APIRouter groups related HTTP routes in a package."
    quizzes = fallbacks.template_quizzes_from_objective(
        chapter={"id": "ch1", "title": "Routers", "objective": "Split routers by package"},
        count=2,
        topic_key="topic-routers",
        theory=theory,
    )
    assert len(quizzes) == 2
    assert quizzes[0]["kind"] == "quiz"
    assert len(quizzes[0]["choices"]) == 4
    assert heuristics.quiz_item_is_usable(quizzes[0], theory=theory, locale="en") is False


def test_quizzes_from_chapter_theory_pass_quality_gate() -> None:
    fallbacks = load_service_module("app.domain.course_from_article.local_course.content.fallbacks")
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    theory = (
        "APIRouter собирает связанные маршруты в отдельном пакете, поэтому импорты "
        "остаются ацикличными. "
        "Один модуль роутера на одну предметную область упрощает ревью. "
        "OpenAPI-схема собирается из аннотаций обработчиков без ручного описания. "
        "Зависимости объявляются через Depends и переиспользуются между маршрутами."
    )
    chapter = {
        "id": "ch1",
        "title": "Почему вы должны попробовать FastAPI?",
        "objective": "Выбрать FastAPI для async OpenAPI",
    }
    ru = fallbacks.quizzes_from_chapter_theory(
        chapter=chapter,
        theory=theory,
        count=3,
        topic_key="t1",
        locale="ru",
    )
    assert len(ru) == 3
    answers = {int(quiz["answer"]) for quiz in ru}
    assert answers

    for quiz in ru:
        assert heuristics.quiz_item_is_usable(quiz, theory=theory, locale="ru") is True
        assert "глава" not in str(quiz["question"]).casefold()
        assert "что говорит глава" not in str(quiz.get("title") or "").casefold()
        assert "описанном сценарии" not in str(quiz["question"]).casefold()
        blob = f"{quiz.get('question')} {quiz.get('choices')}"
        assert "сбор всего в одном месте" not in blob.casefold()
        assert "так, как разобрано" not in blob.casefold()
        assert 0 <= int(quiz["answer"]) <= 3
        assert len(quiz["choices"]) == 4
    theory_en = (
        "APIRouter groups related HTTP routes in a package so imports stay acyclic. "
        "One router module per feature area keeps reviews small. "
        "The OpenAPI schema is built from handler annotations without manual specs. "
        "Dependencies are declared with Depends and reused across routes."
    )
    en = fallbacks.quizzes_from_chapter_theory(
        chapter={"id": "ch1", "title": "Routers", "objective": "Split routers by package"},
        theory=theory_en,
        count=2,
        topic_key="t1",
        locale="en",
    )
    assert len(en) == 2
    for quiz in en:
        assert heuristics.quiz_item_is_usable(quiz, theory=theory_en, locale="en") is True
    drills = fallbacks.practice_from_chapter_theory(
        chapter=chapter,
        theory=theory,
        count=1,
        topic_key="t1",
        locale="ru",
        runtime="python",
    )
    assert len(drills) == 1
    assert (
        heuristics.practice_spec_is_usable(drills[0], locale="ru", theory=theory, runtime="python")
        is True
    )
    assert "NotImplementedError" not in str(drills[0].get("template") or "")
    assert "Допиши" in str(drills[0].get("content") or "")
    assert not str(drills[0].get("title") or "").startswith("Допиши шаг с")
    title = str(drills[0].get("title") or "")
    assert "FastAPI" in title or "APIRouter" in title or "закрепи" in title.casefold()
    java = fallbacks.practice_from_chapter_theory(
        chapter={"id": "ch1", "title": "Producer", "objective": "Send records"},
        theory="Producer sends records into a Kafka topic with a key.",
        count=1,
        topic_key="t1",
        locale="ru",
        runtime="java",
    )
    assert len(java) == 1
    assert "public class" in str(java[0].get("template") or "")
    java_theory = "Producer sends records into a Kafka topic with a key."
    assert (
        heuristics.practice_spec_is_usable(java[0], locale="ru", theory=java_theory, runtime="java")
        is True
    )
    javascript = fallbacks.practice_from_chapter_theory(
        chapter={"id": "ch1", "title": "State update", "objective": "Update state"},
        theory="A state transition produces the next value from the current value.",
        count=1,
        topic_key="t2",
        locale="en",
        runtime="javascript",
    )
    sql = fallbacks.practice_from_chapter_theory(
        chapter={"id": "ch1", "title": "Row filtering", "objective": "Filter rows"},
        theory="A filter keeps only rows that satisfy the stated condition.",
        count=1,
        topic_key="t3",
        locale="en",
        runtime="sql",
    )
    assert len(javascript) == 1
    assert "function " in str(javascript[0].get("template") or "")
    assert "def " not in str(javascript[0].get("template") or "")
    assert len(sql) == 1
    assert "SELECT " in str(sql[0].get("template") or "")
    assert "def " not in str(sql[0].get("template") or "")


def test_practice_unwraps_java_dict_and_fence() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    nested = heuristics.normalize_practice_task(
        {
            "title": "Kafka producer",
            "content": "Допиши отправку в топик email_notifications без GUI.",
            "template": {
                "java": [
                    "import org.apache.kafka.clients.producer.KafkaProducer;",
                    "public class Demo {",
                    "  // TODO",
                    "}",
                ]
            },
        }
    )
    assert "KafkaProducer" in str(nested["template"])
    assert not str(nested["template"]).strip().startswith("{")
    fenced = heuristics.normalize_practice_task(
        {
            "title": "Kafka basics",
            "content": "Допиши класс KafkaBasics по теории главы.",
            "template": {"template": "```java\npublic class KafkaBasics {\n}\n```\n"},
        }
    )
    assert str(fenced["template"]).startswith("public class")
    assert "```" not in str(fenced["template"])


@pytest.mark.asyncio
async def test_local_topic_theory_builds_step() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")

    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-balanced", model=target.model)
    body = SimpleNamespace(locale="ru", runtime="python", runtime_version="3.12")

    async def fake_expand(*_args, **_kwargs):
        return {
            "id": "ch1",
            "kind": "theory",
            "title": "Routers",
            "content": "## Routers\n\nUse APIRouter for packages.",
            "chapter_id": "ch1",
        }

    with patch.object(topic_loop, "expand_local_theory_chapter", new=fake_expand):
        step = await topic_loop.generate_topic_theory(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "Routers",
                "objective": "Split routers",
                "source_excerpt": "APIRouter keeps imports acyclic.",
            },
            policy=policy,
        )
    assert step["kind"] == "theory"
    assert "APIRouter" in str(step["content"]) or "Routers" in str(step["content"])


@pytest.mark.asyncio
async def test_quiz_generation_uses_small_batches_and_resume() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")

    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="cpu-light", model=target.model)
    body = SimpleNamespace(locale="en", runtime="python", runtime_version="3.12")
    chapter = {
        "id": "ch1",
        "title": "Routers",
        "objective": "Split routers by package",
    }
    theory = {"content": "## Routers\n\nUse APIRouter to keep imports acyclic.\n"}
    calls: list[str] = []
    schemas: list[object] = []
    persisted: list[int] = []

    fresh_questions = (
        "Which files land in one package when APIRouter groups a feature area?",
        "When does an acyclic import graph break after a router move?",
    )

    def _payload(index: int) -> str:
        return json.dumps(
            {
                "question": fresh_questions[index % len(fresh_questions)],
                "choices": [
                    "Related HTTP routes",
                    "GPU kernels only",
                    "CSS selectors",
                    "DNS records",
                ],
                "answer": 0,
            }
        )

    async def fake_json(*_args, **kwargs):
        calls.append(str(kwargs.get("user_message") or ""))
        schemas.append(kwargs.get("json_schema"))
        return SimpleNamespace(content=_payload(len(calls) - 1))

    already = [
        {
            "id": "topic-routers-quiz-1",
            "kind": "quiz",
            "title": "Check 1",
            "question": "What does APIRouter group in a FastAPI package layout?",
            "choices": ["Related HTTP routes", "Pixels", "Fonts", "Caches"],
            "answer": 0,
        }
    ]

    with patch.object(
        topic_loop, "complete_json_chat_result", new=AsyncMock(side_effect=fake_json)
    ):
        quizzes = await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter=chapter,
            theory=theory,
            count=3,
            policy=policy,
            topic_key="topic-routers",
            warnings=[],
            already=already,
            persist=lambda rows: persisted.append(len(rows)),
        )

    assert len(quizzes) == 3
    assert quizzes[0]["question"].startswith("What does APIRouter group")
    assert len(calls) == 2
    assert "Need exactly 1 NEW quizzes" in calls[0]
    assert "Return one object:" in calls[0]
    assert "chapter theory" in calls[0].casefold()
    assert schemas[0] == topic_loop.QUIZ_ITEM_SCHEMA
    assert persisted == [2, 3]


def test_theory_fallback_varies_stems_beyond_the_term_count() -> None:
    fallbacks = load_service_module("app.domain.course_from_article.local_course.content.fallbacks")
    theory = (
        "Репликация в Redis копирует поток команд с мастера на реплику. "
        "Реплика отвечает на чтение, но не принимает запись. "
        "Sentinel следит за мастером и запускает переключение при отказе. "
        "Переключение меняет роль реплики на мастер и переписывает конфигурацию."
    )
    chapter = {"id": "ch1", "title": "Репликация и отказоустойчивость", "objective": "Понять роли"}
    quizzes = fallbacks.quizzes_from_chapter_theory(
        chapter=chapter,
        theory=theory,
        count=6,
        topic_key="t1",
        locale="ru",
    )
    stems = {str(quiz["question"]) for quiz in quizzes}
    assert len(quizzes) == 6
    assert len(stems) == 6
    assert all("описанном сценарии" not in str(q["question"]).casefold() for q in quizzes)
    assert all("что говорит глава" not in str(q.get("title") or "").casefold() for q in quizzes)


def test_theory_fallback_skips_weak_morphology_terms() -> None:
    fallbacks = load_service_module("app.domain.course_from_article.local_course.content.fallbacks")
    theory = (
        "Определяющий атрибут объекта храниться в словаре экземпляра. "
        "Изменяемый список как значение по умолчанию сохраняет состояние между вызовами."
    )
    chapter = {
        "id": "ch1",
        "title": "Плохой пример",
        "objective": "Не использовать mutable default",
    }
    quizzes = fallbacks.quizzes_from_chapter_theory(
        chapter=chapter,
        theory=theory,
        count=4,
        topic_key="t9",
        locale="ru",
    )
    blob = " ".join(f"{q.get('title')} {q.get('question')}" for q in quizzes).casefold()
    assert "определяющий" not in blob
    assert "храниться" not in blob
    assert "listing" not in blob


@pytest.mark.asyncio
async def test_chapter_rejects_partial_quizzes_when_theory_runs_out() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")

    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="en", runtime="python", runtime_version="3.12")
    already = [
        {
            "id": "ch1-quiz-1",
            "kind": "quiz",
            "title": "Check 1",
            "question": "What does APIRouter group in a FastAPI package layout?",
            "choices": ["Related HTTP routes", "Pixels", "Fonts", "Caches"],
            "answer": 0,
        }
    ]
    with (
        patch.object(topic_loop, "_quiz_chunk", new=AsyncMock(return_value=[])),
        patch.object(topic_loop, "quizzes_from_chapter_theory", return_value=[]),
        pytest.raises(topic_loop.TutorError, match="required 4 distinct questions"),
    ):
        await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter={"id": "ch1", "title": "Routers", "objective": "Split routers by package"},
            theory={"content": "Use APIRouter to keep imports acyclic."},
            count=4,
            policy=policy,
            topic_key="ch1",
            warnings=[],
            already=already,
        )


@pytest.mark.asyncio
async def test_chapter_without_any_quiz_still_fails_loudly() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")

    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="en", runtime="python", runtime_version="3.12")

    with (
        patch.object(topic_loop, "_quiz_chunk", new=AsyncMock(return_value=[])),
        patch.object(topic_loop, "quizzes_from_chapter_theory", return_value=[]),
        pytest.raises(topic_loop.TutorError),
    ):
        await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter={"id": "ch1", "title": "Routers", "objective": "Split routers by package"},
            theory={"content": "Use APIRouter to keep imports acyclic."},
            count=4,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )


@pytest.mark.asyncio
async def test_generate_topic_quizzes_skips_when_author_disabled() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(
        locale="ru",
        include_quizzes=False,
        runtime="python",
        runtime_version="3.12",
    )
    llm = AsyncMock()
    with patch.object(topic_loop, "complete_json_chat_result", new=llm):
        quizzes = await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter={"id": "ch1", "title": "Routers", "objective": "Split routers"},
            theory={"content": "Use APIRouter to keep imports acyclic."},
            count=4,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )
    assert quizzes == []
    llm.assert_not_called()


@pytest.mark.asyncio
async def test_generate_topic_practice_skips_when_author_disabled() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(
        locale="ru",
        include_code=False,
        runtime="python",
        runtime_version="3.12",
    )
    llm = AsyncMock()
    with patch.object(topic_loop, "complete_json_chat_result", new=llm):
        tasks = await topic_loop.generate_topic_practice(
            AsyncMock(),
            target,
            body=body,
            chapter={"id": "ch1", "title": "Routers", "objective": "Split routers"},
            theory={"content": "Use APIRouter to keep imports acyclic."},
            count=3,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )
    assert tasks == []
    llm.assert_not_called()


def test_local_topic_ready_rejects_ungrounded_quizzes() -> None:
    runner = load_service_module("app.domain.course_from_article.local_course.runtime.runner")
    body = CourseFromArticleRequest(
        article="x" * 200,
        locale="en",
        include_theory=True,
        include_quizzes=True,
        include_code=False,
        quiz_count=1,
    )
    theory_steps = [
        {
            "content": ("APIRouter groups related HTTP routes in a package. " * 12),
            "title": "Routers",
        }
    ]
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
    grounded = {
        "question": "What does APIRouter group in a FastAPI package?",
        "choices": ["Related HTTP routes", "GPU kernels", "CSS files", "DNS records"],
        "answer": 0,
    }
    assert not runner._local_topic_ready(
        body,
        theory_steps=theory_steps,
        quizzes=[generic],
        codes=[],
        quiz_n=1,
        practice_n=0,
    )
    assert runner._local_topic_ready(
        body,
        theory_steps=theory_steps,
        quizzes=[grounded],
        codes=[],
        quiz_n=1,
        practice_n=0,
    )
    dump = "APIRouter groups related HTTP routes in a package so imports stay acyclic. " * 8
    assert not runner._local_topic_ready(
        body,
        theory_steps=[{"content": dump, "title": "Routers"}],
        quizzes=[grounded],
        codes=[],
        quiz_n=1,
        practice_n=0,
        excerpt=dump.strip(),
    )


@pytest.mark.asyncio
async def test_local_theory_uses_composed_prose_prompt() -> None:
    theory_mod = load_service_module("app.domain.course_from_article.local_course.content.theory")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    prompts: list[str] = []
    excerpt = (
        "APIRouter groups related HTTP routes in a package so imports stay tidy. "
        "Keep router imports acyclic so packages load without circular graphs."
    )
    draft = (
        "You import two routers and the app never starts. "
        "Give each feature area one router module and include it from the app once. "
        "Shared models belong in a third package, not in a cycle between routers. "
        "Register the router with an explicit prefix so paths stay stable. "
        "If two packages import each other through routers, application startup fails. "
        "A beginner trap is importing router A from package B and router B from package A. "
        "Name the idea after the example: one feature, one router, one prefix. "
    )

    continues: list[int] = []
    token_caps: list[int] = []

    async def fake_complete(*_args, **kwargs):
        prompts.append(str(kwargs.get("system_prompt") or ""))
        continues.append(int(kwargs.get("max_continues") or 0))
        token_caps.append(int(kwargs.get("max_tokens") or 0))
        return draft

    body = CourseFromArticleRequest(article=excerpt, locale="en")
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    from dataclasses import replace

    policy = replace(policy, strategy_pack="author-full")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    with patch.object(theory_mod, "complete_text_until_done", new=fake_complete):
        step = await theory_mod.expand_local_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "APIRouter packages",
                "objective": "Group routes",
                "source_excerpt": excerpt,
            },
            policy=policy,
        )
    assert step["kind"] == "theory"
    assert prompts
    joined = "\n".join(prompts).casefold()
    assert "curriculum architect" in joined
    assert "plain markdown only" in joined
    assert "fragment" in joined or "excerpt" in joined
    assert continues
    assert continues[0] == policy.theory_max_continues
    assert token_caps
    assert token_caps[0] == policy.theory_section_max_tokens


@pytest.mark.asyncio
async def test_cpu_course_sends_one_source_sentence_per_llm_call() -> None:
    theory_mod = load_service_module("app.domain.course_from_article.local_course.content.theory")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    excerpt = (
        "First source fact explains why the worker stores a durable checkpoint. "
        "Second source fact explains how the worker resumes after a restart. "
        "Third source fact explains when the completed checkpoint is removed."
    )
    requests: list[str] = []

    async def fake_complete(*_args, **kwargs):
        requests.append(str(kwargs.get("user_message") or ""))
        section = len(requests)
        details = " ".join(
            f"Detail {section}-{index} explains the source with a concrete consequence."
            for index in range(12)
        )
        return f"Section {section} teaches one source fact. {details}"

    body = CourseFromArticleRequest(article=excerpt, locale="en")
    policy = policy_mod.local_course_policy_for(profile="cpu-light", model="qwen2.5:3b")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:3b", num_ctx=4096)
    with patch.object(theory_mod, "complete_text_until_done", new=fake_complete):
        step = await theory_mod.expand_local_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "Three source facts",
                "objective": "Teach every fact",
                "source_excerpt": excerpt,
            },
            policy=policy,
        )

    assert step["kind"] == "theory"
    assert len(requests) == 3
    assert "First source fact" in requests[0]
    assert "Second source fact" not in requests[0]
    assert "Second source fact" in requests[1]
    assert "Third source fact" in requests[2]


@pytest.mark.asyncio
async def test_theory_window_raises_when_llm_errors() -> None:
    import httpx

    theory_mod = load_service_module("app.domain.course_from_article.local_course.content.theory")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    excerpt = (
        "APIRouter groups related HTTP routes in a package so imports stay acyclic. "
        "Keep one router module per feature area."
    )

    async def boom(*_args, **_kwargs):
        raise httpx.ConnectError(
            "ollama down",
            request=httpx.Request("POST", "http://ollama:11434/v1/chat/completions"),
        )

    body = CourseFromArticleRequest(article=excerpt, locale="en")
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    with (
        patch.object(theory_mod, "complete_text_until_done", new=boom),
        pytest.raises(theory_mod.TutorError, match="local theory failed"),
    ):
        await theory_mod.expand_local_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "APIRouter packages",
                "objective": "Group routes",
                "source_excerpt": excerpt,
            },
            policy=policy,
        )


@pytest.mark.asyncio
async def test_quiz_husk_json_compiles_from_theory() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="ru", runtime="python", runtime_version="3.12")
    theory = {
        "content": (
            "APIRouter собирает связанные маршруты в пакете, поэтому импорты остаются "
            "ацикличными. "
            "Один модуль роутера на предметную область упрощает ревью. "
            "OpenAPI-схема собирается из аннотаций обработчиков. "
            "Зависимости объявляются через Depends и переиспользуются между маршрутами."
        )
    }

    async def husk(*_args, **_kwargs):
        return SimpleNamespace(content='{"quizzes":[{}]}')

    warnings: list[str] = []
    with patch.object(topic_loop, "complete_json_chat_result", new=AsyncMock(side_effect=husk)):
        quizzes = await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "t1",
                "title": "Почему вы должны попробовать FastAPI?",
                "objective": "Выбрать FastAPI для async OpenAPI",
            },
            theory=theory,
            count=2,
            policy=policy,
            topic_key="t1",
            warnings=warnings,
        )
    assert len(quizzes) == 2
    assert warnings
    for quiz in quizzes:
        assert heuristics.quiz_item_is_usable(quiz, theory=str(theory["content"]), locale="ru")


@pytest.mark.asyncio
async def test_quiz_http_error_compiles_from_theory() -> None:
    import httpx

    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="cpu-light", model=target.model)
    body = SimpleNamespace(locale="ru", runtime="python", runtime_version="3.12")
    theory = {
        "content": (
            "APIRouter держит импорты ацикличными, когда маршруты лежат в отдельном пакете. "
            "Один модуль роутера на предметную область упрощает ревью. "
            "Схема OpenAPI собирается из аннотаций обработчиков. "
            "Зависимости объявляются через Depends и переиспользуются между маршрутами."
        )
    }

    async def boom(*_args, **_kwargs):
        raise httpx.ConnectError(
            "ollama down",
            request=httpx.Request("POST", "http://ollama:11434/v1/chat/completions"),
        )

    warnings: list[str] = []
    with patch.object(topic_loop, "complete_json_chat_result", new=boom):
        quizzes = await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "Routers",
                "objective": "Split routers by package",
            },
            theory=theory,
            count=1,
            policy=policy,
            topic_key="ch1",
            warnings=warnings,
        )
    assert len(quizzes) == 1
    assert heuristics.quiz_item_is_usable(quizzes[0], theory=str(theory["content"]), locale="ru")
    assert warnings


def test_share_count_splits_phased_totals() -> None:
    runner = load_service_module("app.domain.course_from_article.local_course.runtime.runner")
    assert [runner._share_count(5, 3, index) for index in range(3)] == [2, 2, 1]
    assert [runner._share_count(2, 5, index) for index in range(5)] == [1, 1, 0, 0, 0]
    assert runner._share_count(0, 3, 0) == 0


def test_theory_copies_excerpt_rejects_pasted_source() -> None:
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    excerpt = (
        "APIRouter groups related HTTP routes in a package so imports stay acyclic "
        "when each feature owns its own router module."
    )
    assert heuristics.theory_copies_excerpt(excerpt, excerpt) is True
    wrapped = f"{excerpt} "
    assert heuristics.theory_copies_excerpt(wrapped, excerpt) is True
    taught = (
        "You hit circular imports when every route lives in main. "
        "APIRouter keeps related HTTP routes in a package so imports stay acyclic. "
        "Put the router next to the feature, not in the app factory."
    )
    assert heuristics.theory_copies_excerpt(taught, excerpt) is False


def test_syllabus_rejects_title_only_excerpts() -> None:
    outline = load_service_module("app.domain.course_from_article.local_course.curriculum.outline")
    assert (
        outline.syllabus_has_excerpts([{"title": "Routers", "source_excerpt": "Routers"}]) is False
    )
    assert (
        outline.syllabus_has_excerpts(
            [
                {
                    "title": "Routers",
                    "source_excerpt": "APIRouter groups related HTTP routes in a package.",
                }
            ]
        )
        is True
    )


def test_syllabus_rejects_cloned_whole_article_excerpts() -> None:
    outline = load_service_module("app.domain.course_from_article.local_course.curriculum.outline")
    dump = "APIRouter groups related HTTP routes. Depends injects a database session."
    cloned = [
        {"title": "Routers", "source_excerpt": dump},
        {"title": "Depends", "source_excerpt": dump},
        {"title": "Path ops", "source_excerpt": dump},
    ]
    assert outline.syllabus_has_excerpts(cloned) is False
    distinct = [
        {"title": "Routers", "source_excerpt": "APIRouter groups related HTTP routes."},
        {"title": "Depends", "source_excerpt": "Depends injects a database session."},
    ]
    assert outline.syllabus_has_excerpts(distinct) is True


def test_chapter_with_source_does_not_dump_article_into_title_only() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    article = "APIRouter groups related HTTP routes so imports stay acyclic."
    title_only = topic_loop._chapter_with_source(
        {"id": "c1", "title": "Routers", "source_excerpt": "Routers"},
        article,
    )
    assert title_only["source_excerpt"] == "Routers"
    kept = topic_loop._chapter_with_source(
        {
            "id": "c1",
            "title": "Routers",
            "source_excerpt": "APIRouter groups related HTTP routes in a package.",
        },
        article,
    )
    assert "APIRouter groups related HTTP routes in a package." in kept["source_excerpt"]


def test_local_prompts_load_domain_overlay() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    from app.domain.course_from_article.common.runtime.course_context import set_course_profile

    set_course_profile("humanities")
    try:
        theory = messages.theory_system_prompt("ru")
        practice = messages.practice_system_prompt("ru")
        assert "curriculum architect" in theory.casefold()
        assert "small local model" in theory.casefold()
        assert "Narrative" in theory or "counter-reading" in theory
        assert "syllabus is an argument" in theory.casefold()
        assert (
            "if quizzes on" in theory.casefold()
            or "assess only if on" in theory.casefold()
            or "quizzes *check*" in theory.casefold()
            or "quizzes check" in theory.casefold()
        )
        assert (
            "не выдумывай python" in practice.casefold()
            or "не выдумывай код" in practice.casefold()
        )
        folded_practice = practice.casefold()
        assert (
            "open-task" in folded_practice
            or "open tasks" in folded_practice
            or "no fake python" in folded_practice
        )
    finally:
        set_course_profile("programming")
        code_practice = messages.practice_system_prompt("ru")
        set_course_profile("")
    assert "стартовый код" in code_practice.casefold()


def test_local_theory_prompt_honors_quizzes_off() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    from app.domain.course_from_article.common.runtime.course_context import (
        set_course_parts,
        set_course_profile,
    )

    set_course_profile("humanities")
    set_course_parts(theory=True, quizzes=False, practice=False)
    try:
        theory = messages.theory_system_prompt("ru")
        folded = theory.casefold()
        assert "quizzes: off" in folded
        assert "practice: off" in folded
        assert "skill: quiz assessment design" not in folded
        assert "complete book" in folded
        assert "do not invent a missing part" in folded
    finally:
        set_course_parts(theory=True, quizzes=True, practice=True)
        set_course_profile("")


def test_theory_prompt_asks_to_cover_excerpt() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    system = messages.theory_system_prompt()
    folded = system.casefold()
    assert "cover concrete facts" in folded or "cover every concrete fact" in folded
    assert "calm prose" in folded or "calm running prose" in folded
    assert "no labeled pedagogy" in folded or "ловушка" in folded
    user = messages.theory_window_user_message(
        locale="ru",
        title="Routers",
        objective="Split routers by package",
        excerpt="APIRouter groups related HTTP routes.",
        window_index=1,
        window_count=1,
        prior_digest="",
    )
    assert "named fact" in user.casefold() or "Every named API" in user
    assert "Do not copy the excerpt verbatim" in user
    assert "another language" in user
    assert "Russian" in user
    english = messages.theory_window_user_message(
        locale="en",
        title="Routers",
        objective="Split routers by package",
        excerpt="APIRouter groups related HTTP routes.",
        window_index=1,
        window_count=1,
        prior_digest="",
    )
    assert "English" in english
    first = messages.theory_window_user_message(
        locale="ru",
        title="Routers",
        objective="Split routers",
        excerpt="APIRouter groups routes.",
        window_index=1,
        window_count=1,
        prior_digest="",
    )
    assert "epitome" in first.casefold()
    assert "miniature" in first.casefold()
    opening = messages.theory_window_user_message(
        locale="ru",
        title="Routers",
        objective="Split routers",
        excerpt="APIRouter groups routes.",
        window_index=1,
        window_count=2,
        prior_digest="Session is a desk.",
        book_spine={"throughline": "routers → sessions", "address": "ты", "voice": "учебник"},
        next_title="Sessions",
    )
    assert "opening of a new chapter" in opening.casefold()
    assert "already known" in opening.casefold()
    assert "Book throughline" in opening
    assert "Next chapter will be: Sessions" not in opening
    cont = messages.theory_window_user_message(
        locale="ru",
        title="Routers",
        objective="Split routers",
        excerpt="Keep imports acyclic.",
        window_index=2,
        window_count=2,
        prior_digest="APIRouter groups routes.",
        next_title="Sessions",
    )
    assert "Continue THIS chapter" in cont
    assert "Next chapter will be: Sessions" in cont
    assert "course locale" in folded or "translate" in folded
    assert "new introduction" in cont.casefold()


def test_order_prompt_includes_excerpt_density() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    inventory = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.inventory"
    )
    seeds = [
        inventory.TopicSeed(
            title="Routers",
            objective="split",
            excerpt="APIRouter groups related HTTP routes in a package.",
            source_title="A",
            order=0,
        )
    ]
    user = messages.order_user_message(seeds, locale="en")
    assert "APIRouter groups related HTTP routes" in user
    assert "source=A" in user
    assert "merge_groups" in user
    assert "not automatically harder" in user
    assert "epitome" in user.casefold()
    system = messages.order_system_prompt()
    assert "epitome" in system.casefold()


def test_practice_prompt_asks_for_same_skill_ladder() -> None:
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    context = load_service_module("app.domain.course_from_article.common.runtime.course_context")
    context.set_course_parts(theory=True, quizzes=False, practice=True)
    context.set_course_profile("programming")
    try:
        system = messages.practice_system_prompt("ru")
        assert "same skill" in system.casefold()
        user = messages.practice_user_message(
            locale="ru",
            runtime="python",
            runtime_version="3.12",
            chunk=2,
            title="Routers",
            objective="Split routers",
            theory="APIRouter groups routes.",
            already=[],
        )
        assert "ladder" in user.casefold()
        assert "same apis" in user.casefold() or "THIS chapter skill" in user
    finally:
        context.set_course_parts(theory=True, quizzes=True, practice=True)
        context.set_course_profile("")


@pytest.mark.asyncio
async def test_theory_raises_without_source_excerpt() -> None:
    theory_mod = load_service_module("app.domain.course_from_article.local_course.content.theory")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    with pytest.raises(theory_mod.TutorError, match="no source excerpt"):
        await theory_mod.expand_local_theory_chapter(
            AsyncMock(),
            target,
            body=CourseFromArticleRequest(article="x" * 80, locale="en"),
            chapter={
                "id": "ch1",
                "title": "Routers",
                "objective": "Split routers",
                "source_excerpt": "",
            },
            policy=policy,
        )


@pytest.mark.asyncio
async def test_theory_raises_on_title_only_excerpt() -> None:
    theory_mod = load_service_module("app.domain.course_from_article.local_course.content.theory")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    with pytest.raises(theory_mod.TutorError, match="no source excerpt"):
        await theory_mod.expand_local_theory_chapter(
            AsyncMock(),
            target,
            body=CourseFromArticleRequest(article="x" * 80, locale="en"),
            chapter={
                "id": "ch1",
                "title": "Routers",
                "objective": "Split routers",
                "source_excerpt": "Routers",
            },
            policy=policy,
        )


@pytest.mark.asyncio
async def test_practice_http_error_compiles_from_theory() -> None:
    import httpx

    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    heuristics = load_service_module(
        "app.domain.course_from_article.local_course.policy.heuristics"
    )
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="cpu-light", model=target.model)
    body = SimpleNamespace(locale="ru", runtime="python", runtime_version="3.12")
    theory = {"content": "Use APIRouter to keep imports acyclic."}

    async def boom(*_args, **_kwargs):
        raise httpx.ConnectError(
            "ollama down",
            request=httpx.Request("POST", "http://ollama:11434/v1/chat/completions"),
        )

    warnings: list[str] = []
    with patch.object(topic_loop, "complete_json_chat_result", new=boom):
        tasks = await topic_loop.generate_topic_practice(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "Routers",
                "objective": "Split routers by package",
            },
            theory=theory,
            count=1,
            policy=policy,
            topic_key="ch1",
            warnings=warnings,
        )
    assert len(tasks) == 1
    assert heuristics.practice_spec_is_usable(tasks[0], locale="ru", theory=str(theory["content"]))
    assert warnings


@pytest.mark.asyncio
async def test_practice_accepts_russian_brief_without_english_given() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="ru", runtime="python", runtime_version="3.12")
    payload = {
        "tasks": [
            {
                "title": "Собери роутер пакета",
                "content": (
                    "Напиши функцию build_router. Она принимает имя пакета. "
                    "Верни APIRouter с префиксом. Ограничения: без циклов импорта."
                ),
                "template": "",
                "starter": (
                    "from fastapi import APIRouter\n\ndef build_router(name: str):\n    ...\n"
                ),
            }
        ]
    }

    async def fake_json(*_args, **_kwargs):
        return SimpleNamespace(content=json.dumps(payload))

    with patch.object(topic_loop, "complete_json_chat_result", new=fake_json):
        tasks = await topic_loop.generate_topic_practice(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "Routers",
                "objective": "Split routers by package",
            },
            theory={"content": "Use fastapi APIRouter to keep imports acyclic."},
            count=1,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )

    assert len(tasks) == 1
    assert "build_router" in str(tasks[0]["template"])


@pytest.mark.asyncio
async def test_practice_rewrites_solve_stub_from_seven_b() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="ru", runtime="python", runtime_version="3.12")
    payload = {
        "tasks": [
            {
                "title": "Эндпоинт FastAPI health",
                "content": (
                    "Дано: приложение FastAPI. Результат: GET /health отвечает 200. "
                    "Ограничения: без лишних маршрутов."
                ),
                "template": "from fastapi import FastAPI\n\ndef solve():\n    ...\n",
            }
        ]
    }

    async def fake_json(*_args, **_kwargs):
        return SimpleNamespace(content=json.dumps(payload))

    with patch.object(topic_loop, "complete_json_chat_result", new=fake_json):
        tasks = await topic_loop.generate_topic_practice(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "FastAPI intro",
                "objective": "Expose a health route",
            },
            theory={"content": "FastAPI app exposes GET routes via decorators."},
            count=1,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )

    assert len(tasks) == 1
    template = str(tasks[0]["template"])
    assert "def solve(" not in template
    assert "def fastapi(" in template


@pytest.mark.asyncio
async def test_practice_salvages_import_chapter_without_second_llm() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="ru", runtime="python", runtime_version="3.12")
    payload = {
        "tasks": [
            {
                "title": "Импортируем Base из файла настроек БД",
                "content": (
                    "Импортируй Base из нашего файла настроек БД, который мы исправили ранее."
                ),
                "template": "...",
            }
        ]
    }
    calls = {"n": 0}

    async def fake_json(*_args, **_kwargs):
        calls["n"] += 1
        return SimpleNamespace(content=json.dumps(payload))

    with patch.object(topic_loop, "complete_json_chat_result", new=fake_json):
        tasks = await topic_loop.generate_topic_practice(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "Импортируем Base из нашего файла настроек БД",
                "objective": "Импортировать Base из settings",
            },
            theory={
                "content": (
                    "Вынеси declarative_base в модуль настроек.\n"
                    "```python\n"
                    "from app.db.settings import Base\n\n"
                    "class User(Base):\n    pass\n"
                    "```\n"
                )
            },
            count=1,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )

    assert len(tasks) == 1
    assert calls["n"] == 1
    assert "from app.db.settings import Base" in str(tasks[0]["template"])
    assert "Импортируй Base" in str(tasks[0]["content"])


@pytest.mark.asyncio
async def test_retry_local_stage_recovers_after_first_tutor_error(monkeypatch) -> None:
    stage_retry = load_service_module(
        "app.domain.course_from_article.local_course.runtime.stage_retry"
    )
    calls = {"n": 0}

    async def _fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(stage_retry.asyncio, "sleep", _fake_sleep)

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise stage_retry.TutorError(502, "local practice failed for «x»: empty JSON")
        return "ok"

    assert (
        await stage_retry.retry_local_stage(flaky, retries=2, label="practice", title="x") == "ok"
    )
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_retry_local_stage_does_not_retry_missing_excerpt() -> None:
    stage_retry = load_service_module(
        "app.domain.course_from_article.local_course.runtime.stage_retry"
    )
    calls = {"n": 0}

    async def permanent() -> str:
        calls["n"] += 1
        raise stage_retry.TutorError(502, "local theory failed for «x»: no source excerpt")

    with pytest.raises(stage_retry.TutorError, match="no source excerpt"):
        await stage_retry.retry_local_stage(permanent, retries=2, label="theory", title="x")
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_theory_window_retries_then_writes() -> None:
    theory_mod = load_service_module("app.domain.course_from_article.local_course.content.theory")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    excerpt = (
        "APIRouter groups related HTTP routes in a package so imports stay acyclic. "
        "Keep one router module per feature area. Name the router after the package."
    )
    calls = {"n": 0}

    async def flaky(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("empty LLM content")
        return (
            "When a package grows, dumping every path onto one module creates import cycles. "
            "APIRouter keeps the HTTP surface of a feature in one place instead of a god app. "
            "Put users.py next to the user use-cases and include that router from main. "
            "The beginner trap is importing models through the router module; keep that "
            "edge pointing outward. Name the router after the package so grep finds it. "
            "Include the router once from the application factory, not from random helpers. "
            "If two features share a path prefix, split by use-case rather than by HTTP verb. "
            "That is the whole move: one router module per feature area, acyclic imports."
        )

    body = CourseFromArticleRequest(article=excerpt, locale="en")
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model="llama3.1:8b")
    from dataclasses import replace

    policy = replace(policy, strategy_pack="author-full")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "llama3.1:8b", num_ctx=8192)
    with patch.object(theory_mod, "complete_text_until_done", new=flaky):
        step = await theory_mod.expand_local_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "APIRouter packages",
                "objective": "Group routes by package",
                "source_excerpt": excerpt,
            },
            policy=policy,
        )
    assert "APIRouter" in str(step["content"])
    assert calls["n"] >= 2


@pytest.mark.asyncio
async def test_practice_accepts_singular_task_and_string_quiz_answer() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target_mod = load_service_module("app.domain.llm.target")
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "gemma2:9b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="en", runtime="python", runtime_version="3.12")
    practice_payload = {
        "task": {
            "title": "Health endpoint",
            "content": (
                "The handler receives a FastAPI app. It returns GET /health with 200. "
                "Constraints: no extra routes."
            ),
            "template": "from fastapi import FastAPI\n\ndef health():\n    ...\n",
        }
    }
    quiz_payload = {
        "quiz": {
            "title": "Router split",
            "question": "Why keep APIRouter in its own package module?",
            "choices": [
                {"text": "To keep imports acyclic"},
                {"text": "Because FastAPI forbids app.get"},
                {"text": "To skip type hints"},
                {"text": "To hide OpenAPI"},
            ],
            "answer": "0",
        }
    }
    calls = {"n": 0}

    async def fake_json(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return SimpleNamespace(content=json.dumps(practice_payload))
        return SimpleNamespace(content=json.dumps(quiz_payload))

    with patch.object(topic_loop, "complete_json_chat_result", new=fake_json):
        tasks = await topic_loop.generate_topic_practice(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "FastAPI intro",
                "objective": "Expose a health route",
            },
            theory={"content": "FastAPI app exposes GET routes via decorators and APIRouter."},
            count=1,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )
        quizzes = await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter={
                "id": "ch1",
                "title": "FastAPI intro",
                "objective": "Expose a health route",
            },
            theory={"content": "FastAPI app exposes GET routes via decorators and APIRouter."},
            count=1,
            policy=policy,
            topic_key="ch1",
            warnings=[],
        )

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Health endpoint"
    assert len(quizzes) == 1
    assert quizzes[0]["answer"] == 0
    assert quizzes[0]["choices"][0] == "To keep imports acyclic"


@pytest.mark.asyncio
async def test_generate_topic_quizzes_retries_when_stem_duplicates_already() -> None:
    topic_loop = load_service_module(
        "app.domain.course_from_article.local_course.content.topic_loop"
    )
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    target = SimpleNamespace(model="qwen2.5:7b", num_ctx=8192)
    policy = policy_mod.local_course_policy_for(profile="gpu-light", model=target.model)
    body = SimpleNamespace(locale="en", include_quizzes=True)
    chapter = {"id": "ch1", "title": "Routers", "objective": "Split routers by package"}
    theory = {
        "content": (
            "APIRouter groups related HTTP routes in a package so imports stay acyclic. "
            "Keep one router module per feature area."
        )
    }
    already = [
        {
            "id": "ch1-quiz-1",
            "kind": "quiz",
            "title": "Check",
            "question": "What does APIRouter group in a package layout?",
            "choices": ["Related HTTP routes", "GPU kernels", "CSS selectors", "DNS records"],
            "answer": 0,
        }
    ]
    calls: list[str] = []

    async def fake_json(*_args, **kwargs):
        calls.append(str(kwargs.get("user_message") or ""))
        if "CRITICAL" in calls[-1]:
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "question": "Why keep one router module per feature area?",
                        "choices": [
                            "Imports stay acyclic",
                            "GPU kernels only",
                            "CSS selectors",
                            "DNS records",
                        ],
                        "answer": 0,
                    }
                )
            )
        return SimpleNamespace(
            content=json.dumps(
                {
                    "question": "What does APIRouter group in a package layout?",
                    "choices": [
                        "Related HTTP routes",
                        "GPU kernels only",
                        "CSS selectors",
                        "DNS records",
                    ],
                    "answer": 0,
                }
            )
        )

    warnings: list[str] = []
    patch_complete = patch.object(
        topic_loop,
        "complete_json_chat_result",
        new=AsyncMock(side_effect=fake_json),
    )
    with patch_complete:
        quizzes = await topic_loop.generate_topic_quizzes(
            AsyncMock(),
            target,
            body=body,
            chapter=chapter,
            theory=theory,
            count=2,
            policy=policy,
            topic_key="ch1",
            warnings=warnings,
            already=already,
        )

    assert len(quizzes) == 2
    assert "feature area" in str(quizzes[1]["question"]).casefold()
    assert any("CRITICAL" in message for message in calls)
    assert not any("compiled from chapter theory" in item for item in warnings)
