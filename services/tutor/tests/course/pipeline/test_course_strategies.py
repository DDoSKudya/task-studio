from __future__ import annotations

from app.domain.course_from_article.common.runtime.course_context import set_strategy_pack
from app.domain.course_from_article.local_course.policy import policy as policy_mod
from app.domain.course_strategies import (
    audit_course_quality,
    build_chapter_blueprint,
    chapter_title_is_valid,
    choices_are_letter_only,
    detect_practice_runtime,
    filter_skills_for_pack,
    load_strategy,
    montage_theory_from_excerpt,
    parse_document_blocks,
    parse_strategy_pack,
    resolve_strategy_pack_id,
    sanitize_chapter_title,
    strategy_briefs,
)
from app.domain.prompt_compose import course_from_article_system_prompt
from app.domain.prompt_compose.core import PromptRequest
from app.domain.prompt_compose.skills import course_skill_layers


def test_resolve_strategy_pack_ids() -> None:
    assert resolve_strategy_pack_id(meets_minimum=False) == "blocked"

    assert resolve_strategy_pack_id(meets_minimum=True) == "author-full"


def test_parse_preserve_pack_and_briefs() -> None:
    pack = parse_strategy_pack("preserve-7b")
    assert pack.pack_id == "preserve-7b"
    assert "theory/montage-preserve" in pack.strategy_paths
    assert "expand-dense-prose" in pack.skills_skip
    assert "instructional-design" in pack.skills_skip
    assert "code-task-ladder" in pack.skills_skip
    assert "open-task-ladder" in pack.skills_skip
    assert "book-polish" in pack.skills_skip
    assert load_strategy("theory/montage-preserve")
    briefs = strategy_briefs(pack)
    assert "preserve-7b" in briefs
    assert "Montage" in briefs or "montage" in briefs.casefold()


def test_filter_skills_skips_expand_on_preserve() -> None:
    pack = parse_strategy_pack("preserve-7b")
    filtered = filter_skills_for_pack(
        ["anti-hallucination-source", "expand-dense-prose", "quiz-assessment-design"],
        pack,
    )
    assert "expand-dense-prose" not in filtered
    assert "quiz-assessment-design" in filtered
    assert filtered == ["anti-hallucination-source", "quiz-assessment-design"]


def test_filter_skills_clears_all_on_blocked() -> None:
    pack = parse_strategy_pack("blocked")
    assert filter_skills_for_pack(["course-stage-json", "expand-dense-prose"], pack) == []


def test_compose_skips_expand_for_preserve_pack() -> None:
    set_strategy_pack("preserve-7b")
    request = PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="theory",
        step_title="theory",
        strategy_pack="preserve-7b",
    )
    always, _domain, stage = course_skill_layers(request)
    assert "expand-dense-prose" not in stage
    assert "instructional-design" not in always
    assert "code-task-ladder" not in stage

    assert "quiz-assessment-design" not in always
    assert "practice-as-drill" not in always
    assert "quiz-assessment-design" not in stage
    assert "practice-as-drill" not in stage
    assert stage == ["diagram-craft"]
    prompt = course_from_article_system_prompt(
        stage="theory",
        strategy_pack="preserve-7b",
        local_runtime=True,
    )
    assert "Active strategy pack" in prompt or "montage" in prompt.casefold()
    assert "literary, teachable theory" not in prompt.casefold()


def test_compose_preserve_skips_polish_and_open_ladder() -> None:
    polish = PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="polish",
        step_title="polish",
        strategy_pack="preserve-7b",
    )
    _always_p, _domain_p, polish_stage = course_skill_layers(polish)
    assert polish_stage == []

    tasks = PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="tasks",
        step_title="tasks",
        strategy_pack="preserve-7b",
    )
    _always_t, _domain_t, tasks_stage = course_skill_layers(tasks)
    assert "open-task-ladder" not in tasks_stage
    assert tasks_stage == ["practice-as-drill"]

    code = PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="code",
        step_title="code",
        strategy_pack="preserve-7b",
    )
    _always_c, _domain_c, code_stage = course_skill_layers(code)
    assert "code-task-ladder" not in code_stage
    assert code_stage == ["practice-as-drill"]


def test_compose_keeps_expand_for_author_full() -> None:
    request = PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="theory",
        step_title="theory",
        strategy_pack="author-full",
    )
    always, _domain, stage = course_skill_layers(request)
    assert "instructional-design" in always
    assert "expand-dense-prose" in stage
    assert "curriculum-synthesis" not in always
    assert "quiz-assessment-design" not in always
    assert stage == ["expand-dense-prose", "diagram-craft"]


def test_title_and_choice_gates() -> None:
    assert not chapter_title_is_valid(
        "REDIS: такой простой… Меня зовут Андрей и я расскажу про кластер"
    )
    assert not chapter_title_is_valid("***Полноценный кластер*** ![fig](x)")
    clean = sanitize_chapter_title(
        "## Best practices for Redis Cluster",
        fallback="Redis",
    )
    assert chapter_title_is_valid(clean)
    assert len(clean) <= 70
    assert choices_are_letter_only(["A", "B", "C", "D"])
    assert not choices_are_letter_only(["Use SET", "Use GET", "Flush all", "Ignore TTL"])


def test_document_blocks_and_blueprint() -> None:
    md = (
        "## Cluster basics\n\nRedis Cluster shards keys.\n\n"
        "![topology](https://example.com/cluster.png)\n\n"
        "```bash\nredis-cli --cluster create\n```\n"
    )
    blocks = parse_document_blocks(md, source_prefix="s1")
    kinds = {block.kind for block in blocks}
    assert "heading" in kinds
    assert "figure" in kinds
    assert "code" in kinds
    blueprint = build_chapter_blueprint(
        {
            "id": "t1",
            "title": "Cluster basics",
            "objective": "Explain sharding",
            "source_excerpt": md,
            "source_images": "![topology](https://example.com/cluster.png)",
        }
    )
    assert blueprint["key_claims"]
    assert blueprint["required_figures"]
    assert blueprint["visual_plan"]["type"] == "source_figure"


def test_visual_plan_uses_structure_not_course_topic() -> None:
    lifecycle = build_chapter_blueprint(
        {
            "id": "biology",
            "title": "Жизненный цикл звезды",
            "source_excerpt": (
                "Звезда проходит несколько стадий от формирования до завершения эволюции."
            ),
        }
    )
    topic_only = build_chapter_blueprint(
        {
            "id": "async",
            "title": "Сопрограммы asyncio",
            "source_excerpt": (
                "Сопрограмма представляет вычисление, которое можно приостанавливать."
            ),
        }
    )

    assert lifecycle["visual_plan"]["type"] == "mermaid"
    assert topic_only["visual_plan"]["type"] == "none"

    comparison = build_chapter_blueprint(
        {
            "id": "compare",
            "title": "Процессы против потоков",
            "source_excerpt": (
                "Поток разделяет память процесса, а отдельный процесс "
                "изолирует адресное пространство."
            ),
        }
    )
    assert comparison["visual_plan"]["type"] == "mermaid"


def test_montage_includes_figure() -> None:
    content = montage_theory_from_excerpt(
        title="Cluster",
        excerpt="Redis Cluster shards keys across nodes.",
        source_images="![topology](https://example.com/cluster.png)",
        locale="en",
        key_claims=["Cluster shards keys across nodes"],
    )
    assert "![topology](https://example.com/cluster.png)" in content
    assert "Cluster" in content


def test_practice_runtime_from_generic_cli() -> None:
    assert detect_practice_runtime("service-cli apply manifest.yml") == "shell"
    assert detect_practice_runtime("```python\ndef main():\n    pass\n```") == "python"
    assert (
        detect_practice_runtime(
            '# Создаем строку\ntext = "Привет, мир!"\n# TODO: Попытка изменения'
        )
        == ""
    )
    assert detect_practice_runtime("# TODO: заполнить раздел") == ""
    assert detect_practice_runtime('const text = "hello";\n// TODO: update') == "javascript"


def test_audit_l0_title_failure() -> None:
    audit = audit_course_quality(
        chapters=[{"title": "Меня зовут Андрей и это длинное предложение без метки"}],
        theory_steps=[],
        quizzes=[],
        practices=[],
    )
    assert audit.level == "none"
    assert "L0.title_gate" in audit.failed


def test_title_gate_rejects_sentence_fragments() -> None:
    assert not chapter_title_is_valid("Сейчас система поддерживает различные языки,")
    assert not chapter_title_is_valid("Вкратце пробежимся по характеристикам: - Персистентность:")
    assert not chapter_title_is_valid("Sentinel. Эта топология развёртывания применялась")

    assert not chapter_title_is_valid("Недавно я подробно рассказывал об этой")
    assert not chapter_title_is_valid("Replication keeps the replica in")
    assert not chapter_title_is_valid("Запуск большего количества нагрузок на одной")
    assert not chapter_title_is_valid(
        "Запуск большего количества нагрузок на одной и той же аппаратной"
    )
    assert not chapter_title_is_valid(
        "Пример выполнения неблокирующего ввода-вывода с asyncio с помощью"
    )
    assert not chapter_title_is_valid("Получи генератор.")
    assert not chapter_title_is_valid("Получите генератор.")
    assert not chapter_title_is_valid("Руководство часть 3 (13)")
    assert not chapter_title_is_valid("Теория и базовая эксплуатац")
    assert chapter_title_is_valid("Redis vs. Memcached")
    assert chapter_title_is_valid("Модели постоянного хранения данных в Redis")


def test_sanitize_title_prefers_fallback_over_six_word_stub() -> None:
    from app.domain.course_strategies.gates import sanitize_chapter_title

    cleaned = sanitize_chapter_title(
        "Запуск большего количества нагрузок на одной и той же аппаратной",
        fallback="Running more workloads on the same hardware",
    )
    assert not cleaned.endswith(("на одной", "аппаратной"))
    assert "hardware" in cleaned.casefold() or cleaned == "Запуск большего количества нагрузок"


def test_audit_catches_duplicate_and_embedded_choices() -> None:
    choices = ["Сервер структур данных", "Только кэш", "Очередь сообщений", "Файловая БД"]
    stem = "Чем Redis отличается от обычного кэша в этой главе?"
    audit = audit_course_quality(
        chapters=[{"title": "Архитектура Redis"}],
        theory_steps=[{"content": "Redis хранит структуры данных в памяти."}],
        quizzes=[
            {"question": stem, "choices": choices},
            {"question": f"{stem}\n\nA) {choices[0]}\nB) {choices[1]}", "choices": choices},
        ],
        practices=[{"checker": "llm", "tests": [], "runtime": "", "template": "```sql\n-- TODO"}],
        phase_order=["study", "assess", "practice"],
    )
    assert "L3.duplicate_quiz_stems" in audit.failed
    assert "L3.choices_inside_question" in audit.failed
    assert "L3.practice_not_runnable" in audit.failed
    assert "L3.practice_runtime_missing" in audit.failed
    assert "L3.practice_template_markdown" in audit.failed
    assert audit.level != "L3"


def test_audit_penalizes_compiled_quizzes_shortfall_and_open_practice() -> None:
    audit = audit_course_quality(
        chapters=[{"title": "Управление процессами"}],
        theory_steps=[{"content": "Процесс запускается командой и сохраняет состояние."}],
        quizzes=[
            {
                "id": "process-quiz-g1",
                "generation": "compiled",
                "question": "Как запускается процесс?",
                "choices": ["Командой", "Случайно", "Таймером", "Записью"],
            }
        ],
        practices=[{"kind": "task", "checker": "llm", "tests": [], "runtime": "bash"}],
        warnings=[
            "local quizzes: chapter kept 3 of 4 questions — theory ran out",
            "practice: open tasks (not a code editor)",
        ],
        expects_executable_practice=True,
    )

    assert "L3.compiled_quiz_fallback" in audit.must_fix
    assert "L3.quiz_count_shortfall" in audit.must_fix
    assert "L3.open_practice_for_tool_course" in audit.must_fix
    assert "L2.visual_missing" in audit.must_fix
    assert audit.score < 60


def test_audit_penalizes_tiny_template_and_weak_reinforcement() -> None:
    audit = audit_course_quality(
        chapters=[{"title": "Практическое применение"}],
        theory_steps=[{"content": "Материал описывает последовательность действий."}],
        quizzes=[],
        practices=[
            {
                "kind": "code",
                "checker": "llm",
                "runtime": "custom",
                "template": "// TODO",
                "tests": [],
            }
        ],
        warnings=[
            "practice quality gate weak after reinforce: Apply operation "
            "(score~0.58; code template is empty or tiny)"
        ],
    )

    assert "L3.practice_template_tiny" in audit.must_fix
    assert "L3.practice_quality_low" in audit.must_fix
    assert audit.score <= 45


def test_audit_tracks_code_template_fallback_after_conversion() -> None:
    audit = audit_course_quality(
        chapters=[{"title": "Практическое применение"}],
        theory_steps=[{"content": "Материал описывает последовательность действий."}],
        quizzes=[],
        practices=[
            {
                "kind": "task",
                "checker": "llm",
                "runtime": "custom",
                "content": "Опишите решение и ожидаемый результат.",
            }
        ],
        warnings=["practice converted to open task after weak code template: Apply operation"],
    )

    assert "L3.practice_template_tiny" in audit.must_fix


def test_montage_does_not_repeat_the_same_bridge() -> None:
    excerpt = "\n\n".join(
        f"Абзац номер {index} подробно описывает поведение Redis в этом режиме работы."
        for index in range(6)
    )
    content = montage_theory_from_excerpt(title="Персистентность", excerpt=excerpt, locale="ru")
    assert content.count("Дальше по тому же разделу") == 0
    assert "Ниже — ключевые положения из исходного раздела." in content
    assert "Абзац номер 3" in content


def test_ensure_mermaid_from_visual_plan_when_missing() -> None:
    from app.domain.course_strategies import ensure_mermaid_from_visual_plan

    body = "Docker daemon принимает запросы клиента и управляет контейнерами."
    filled = ensure_mermaid_from_visual_plan(
        body,
        visual_plan={"type": "mermaid"},
        title="Архитектура Docker",
        key_claims=["Клиент говорит с daemon", "Daemon запускает контейнеры"],
        locale="ru",
    )
    assert "```mermaid" in filled
    assert "Архитектура Docker" in filled
    assert (
        ensure_mermaid_from_visual_plan(
            filled, visual_plan={"type": "mermaid"}, title="x", locale="ru"
        ).count("```mermaid")
        == 1
    )


def test_local_policy_preserves_volume_and_quality_on_3b_and_7b() -> None:
    cpu = policy_mod.local_course_policy_for(profile="cpu-light", model="qwen2.5:3b")
    seven = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    assert cpu.strategy_pack == seven.strategy_pack == "author-full"
    assert cpu.max_chapters == seven.max_chapters
    assert cpu.quality_rounds == seven.quality_rounds
    assert cpu.section_quality_rounds == seven.section_quality_rounds
    assert cpu.run_polish is seven.run_polish is True
    assert cpu.sentences_per_window < seven.sentences_per_window
    assert cpu.topic_retries > seven.topic_retries
    assert "strategy=cpu" in (cpu.warning or "")
    assert "strategy=standard" in (seven.warning or "")
