from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from tutor_helpers.loaders import load_service_module


def _score(evaluate, *, coverage: float, quiz: float, practice: float, title: str = "article"):
    return evaluate.ArticleScore(
        title=title,
        heading_coverage=coverage,
        quiz_grounded=quiz,
        practice_io=practice,
    )


def _report(evaluate, score, n: int = 20):
    return evaluate.EvalReport(scores=tuple(score for _ in range(n)))


def _usable_quiz(theory: str) -> dict[str, object]:
    token = next(part for part in theory.replace("#", " ").split() if len(part) > 4)
    return {
        "question": f"Which statement about {token} matches this chapter?",
        "choices": [
            f"{token} is explained in the chapter theory",
            "The chapter never mentions this idea at all",
            "Skip the article and memorize only the title",
            "Replace the chapter with unrelated trivia",
        ],
        "answer": 0,
    }


def _usable_practice() -> dict[str, object]:
    return {
        "title": "Practice the chapter idea",
        "content": (
            "Given: a short input from the chapter. "
            "Expected: printed result on stdout. "
            "Constraints: keep the function tiny."
        ),
        "template": "def solve() -> str:\n    return 'ok'\n",
    }


def _filled_build(store_mod, tmp_path: Path):
    store = store_mod.CourseBuildStore(tmp_path / "builds", ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "FastAPI", "locale": "ru"},
        title="FastAPI",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    chapters = [
        {
            "id": "t1",
            "title": "Minimal app",
            "objective": "Create FastAPI()",
            "source_excerpt": "FastAPI builds JSON APIs with type hints.",
        },
        {
            "id": "t2",
            "title": "Path operations",
            "objective": "Bind HTTP routes",
            "source_excerpt": "A path operation is a function bound to HTTP method and path.",
        },
    ]
    inventory = [
        {
            "title": item["title"],
            "objective": item["objective"],
            "excerpt": item["source_excerpt"],
        }
        for item in chapters
    ]
    store.save_compiler(
        user_id,
        build_id,
        {"chapters": chapters, "outcomes": ["learn FastAPI"], "inventory": inventory},
    )
    for chapter in chapters:
        store.save_topic(
            user_id,
            build_id,
            chapter["id"],
            theory={
                "title": chapter["title"],
                "objective": chapter["objective"],
                "source_excerpt": chapter["source_excerpt"],
                "content": chapter["source_excerpt"] + " Write a lesson from this excerpt.",
            },
            quizzes=[_usable_quiz(chapter["source_excerpt"])],
            codes=[_usable_practice()],
        )
    return store, user_id, build_id


def test_eval_corpus_has_exactly_twenty_articles() -> None:
    corpus = load_service_module("app.domain.course_adapters.eval_corpus")
    assert corpus.eval_article_count() == 20
    assert len(corpus.EVAL_ARTICLES) == 20


def test_compiler_baseline_scores_all_twenty() -> None:
    evaluate = load_service_module("app.domain.course_adapters.evaluate")
    report = evaluate.compiler_baseline()
    assert report.article_count == 20
    assert report.mean > 0


def test_equal_adapter_does_not_beat_compiler() -> None:
    evaluate = load_service_module("app.domain.course_adapters.evaluate")
    same = _report(evaluate, _score(evaluate, coverage=0.8, quiz=0.5, practice=0.5))
    assert evaluate.adapter_beats_compiler(same, same) is False
    with pytest.raises(evaluate.AdapterRefused):
        evaluate.assert_adapter_ships(role="course-map", adapter=same, compiler=same)


def test_weaker_adapter_does_not_ship() -> None:
    evaluate = load_service_module("app.domain.course_adapters.evaluate")
    adapter = _report(evaluate, _score(evaluate, coverage=0.4, quiz=0.2, practice=0.2))
    compiler = _report(evaluate, _score(evaluate, coverage=0.8, quiz=0.5, practice=0.5))
    assert evaluate.adapter_beats_compiler(adapter, compiler) is False
    with pytest.raises(evaluate.AdapterRefused):
        evaluate.assert_adapter_ships(
            role="course-theory",
            adapter=adapter,
            compiler=compiler,
        )


def test_coverage_drop_beyond_slack_refuses_even_if_mean_is_higher() -> None:
    evaluate = load_service_module("app.domain.course_adapters.evaluate")
    adapter = _report(evaluate, _score(evaluate, coverage=0.90, quiz=1.0, practice=1.0))
    compiler = _report(evaluate, _score(evaluate, coverage=1.0, quiz=0.2, practice=0.2))
    assert adapter.mean > compiler.mean
    assert evaluate.adapter_beats_compiler(adapter, compiler) is False


def test_better_adapter_within_coverage_slack_ships(tmp_path: Path) -> None:
    evaluate = load_service_module("app.domain.course_adapters.evaluate")
    ship = load_service_module("app.domain.course_adapters.ship")
    registry = load_service_module("app.domain.course_adapters.registry")
    adapter = _report(evaluate, _score(evaluate, coverage=0.99, quiz=0.9, practice=0.9))
    compiler = _report(evaluate, _score(evaluate, coverage=1.0, quiz=0.4, practice=0.4))
    assert evaluate.adapter_beats_compiler(adapter, compiler) is True
    registry_path = tmp_path / "registry.json"
    book = ship.ship_adapter(
        role="course-quiz",
        adapter=adapter,
        compiler=compiler,
        registry_path=registry_path,
    )
    entry = book.shipped("course-quiz")
    assert entry is not None
    assert entry.model == "task-studio-course-quiz:latest"
    loaded = registry.load_registry(registry_path)
    assert loaded.shipped("course-quiz") is not None
    assert loaded.shipped("course-theory") is None


def test_short_eval_corpus_cannot_ship() -> None:
    evaluate = load_service_module("app.domain.course_adapters.evaluate")
    adapter = _report(
        evaluate,
        _score(evaluate, coverage=1.0, quiz=1.0, practice=1.0),
        n=19,
    )
    compiler = _report(
        evaluate,
        _score(evaluate, coverage=0.5, quiz=0.5, practice=0.5),
        n=19,
    )
    assert evaluate.adapter_beats_compiler(adapter, compiler) is False


def test_harvest_survives_discard(tmp_path: Path) -> None:
    gold_mod = load_service_module("app.domain.course_adapters.gold")
    store_mod = load_service_module("app.domain.course_build.store")
    checkpoint = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_checkpoint"
    )
    store, user_id, build_id = _filled_build(store_mod, tmp_path)
    gold = gold_mod.GoldStore(tmp_path / "gold")
    written = gold_mod.harvest_from_build(store, gold, user_id=user_id, build_id=build_id)
    assert written >= 4
    assert gold.count("course-map") == 1
    assert gold.count("course-theory") == 2
    assert gold.count("course-quiz") == 2
    assert gold.count("course-practice") == 2
    assert gold.count("tutor-chat") == 0
    checkpoint.mark_build_done(store, user_id=user_id, build_id=build_id)
    assert store.exists(user_id, build_id)
    store.discard(user_id, build_id)
    assert not store.exists(user_id, build_id)
    assert gold.count("course-map") == 1
    assert (tmp_path / "gold" / "course-map.jsonl").is_file()


def test_assert_gold_ready_refuses_empty(tmp_path: Path) -> None:
    gold_mod = load_service_module("app.domain.course_adapters.gold")
    gold = gold_mod.GoldStore(tmp_path / "gold")
    with pytest.raises(gold_mod.AdapterRefused):
        gold_mod.assert_gold_ready(gold, "course-map")


def test_prepare_train_job_refuses_without_gold(tmp_path: Path) -> None:
    export = load_service_module("app.domain.course_adapters.export")
    gold = export.GoldStore(tmp_path / "gold")
    with pytest.raises(export.AdapterRefused):
        export.prepare_train_job(gold, "course-map", workdir=tmp_path / "work")


def test_prepare_train_job_writes_unsloth_script(tmp_path: Path) -> None:
    gold_mod = load_service_module("app.domain.course_adapters.gold")
    gold = gold_mod.GoldStore(tmp_path / "gold")
    gold.append(
        gold_mod.GoldPair(
            role="course-map",
            system="order topics",
            user="Topics:\n0: A\n1: B",
            assistant='{"order": ["0", "1"], "outcomes": ["learn"]}',
        )
    )
    export = load_service_module("app.domain.course_adapters.export")
    job = export.prepare_train_job(
        gold,
        "course-map",
        workdir=tmp_path / "work",
        min_pairs=1,
    )
    script = job.script_path.read_text(encoding="utf-8")
    assert "save_pretrained_gguf" in script
    assert "q4_k_m" in script
    line = job.dataset_path.read_text(encoding="utf-8").splitlines()[0]
    row = json.loads(line)
    assert row["assistant"].startswith("{")


def test_export_gguf_uses_runner(tmp_path: Path) -> None:
    export = load_service_module("app.domain.course_adapters.export")
    gguf = tmp_path / "adapter.gguf"
    gguf.write_bytes(b"GGUF")
    recorded: list[list[str]] = []

    def runner(command, workdir: Path) -> None:
        recorded.append(list(command))
        assert workdir == tmp_path / "course-map"

    job = export.TrainJob(
        role="course-map",
        dataset_path=tmp_path / "course-map" / "dataset.jsonl",
        script_path=tmp_path / "course-map" / "train_qlora.py",
        output_dir=tmp_path / "course-map",
        base_model="unsloth/Qwen2.5-7B-Instruct",
        ollama_name=export.ollama_model_for_role("course-map"),
        quantization="q4_k_m",
        gguf_dir=tmp_path / "course-map" / "gguf",
    )
    name = export.export_gguf_to_ollama(job, gguf_file=gguf, runner=runner)
    assert name == "task-studio-course-map:latest"
    assert recorded[0][:3] == ["ollama", "create", name]
    modelfile = (tmp_path / "course-map" / "Modelfile").read_text(encoding="utf-8")
    assert "FROM " in modelfile
    assert str(gguf.resolve()) in modelfile


def test_export_without_gguf_refuses(tmp_path: Path) -> None:
    export = load_service_module("app.domain.course_adapters.export")
    job = export.TrainJob(
        role="course-quiz",
        dataset_path=tmp_path / "dataset.jsonl",
        script_path=tmp_path / "train_qlora.py",
        output_dir=tmp_path,
        base_model="unsloth/Qwen2.5-7B-Instruct",
        ollama_name=export.ollama_model_for_role("course-quiz"),
        quantization="q4_k_m",
        gguf_dir=tmp_path / "gguf",
    )
    with pytest.raises(export.AdapterRefused):
        export.export_gguf_to_ollama(job)


def test_apply_role_adapter_swaps_only_shipped_installed_role() -> None:
    runtime = load_service_module("app.domain.course_adapters.runtime")
    registry = load_service_module("app.domain.course_adapters.registry")
    target_mod = load_service_module("app.domain.llm.target")
    quiz_model = "task-studio-course-quiz:latest"
    book = registry.AdapterRegistry.empty().with_entry(
        registry.stamp_shipped(
            role="course-quiz",
            model=quiz_model,
            eval_mean=0.8,
            compiler_mean=0.5,
        )
    )
    base = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b")
    installed = ["qwen2.5:7b", quiz_model]
    quiz_target = runtime.apply_role_adapter(
        base,
        "course-quiz",
        registry=book,
        installed=installed,
    )
    theory_target = runtime.apply_role_adapter(
        base,
        "course-theory",
        registry=book,
        installed=installed,
    )
    missing = runtime.apply_role_adapter(
        base,
        "course-quiz",
        registry=book,
        installed=["qwen2.5:7b"],
    )
    assert quiz_target.model == quiz_model
    assert theory_target.model == "qwen2.5:7b"
    assert missing.model == "qwen2.5:7b"
    assert runtime.apply_role_adapter(base, "course-quiz", registry=book).model == "qwen2.5:7b"
    empty = target_mod.LlmTarget(
        "http://ollama:11434/v1",
        None,
        "qwen2.5:7b",
        installed_models=(),
    )
    assert runtime.apply_role_adapter(empty, "course-quiz", registry=book).model == "qwen2.5:7b"


def test_adapter_model_does_not_bypass_course_minimum() -> None:
    roles = load_service_module("app.domain.course_adapters.roles")
    policy = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    select = load_service_module("app.domain.ollama.model_select")
    adapter = "task-studio-course-theory:latest"
    assert roles.is_adapter_model(adapter) is True
    assert policy.model_meets_course_minimum(adapter) is False
    assert select.model_is_course_capable(adapter) is False
    assert policy.model_meets_course_minimum("qwen2.5:1.5b") is False
    assert select.model_is_course_capable("qwen2.5:1.5b") is False
    assert policy.model_meets_course_minimum("qwen2.5:3b") is True
    assert policy.model_meets_course_minimum("qwen2.5:7b") is True
    assert select.model_is_course_capable("qwen2.5:7b") is True
    assert select.model_is_course_capable("llama3.1:8b") is True
    assert select.model_is_course_capable("llama3.1:70b") is True


def test_gold_skips_corrupt_jsonl(tmp_path: Path) -> None:
    gold_mod = load_service_module("app.domain.course_adapters.gold")
    path = tmp_path / "gold" / "course-map.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        "not-json\n"
        + json.dumps(
            {
                "role": "course-map",
                "system": "sys",
                "user": "user",
                "assistant": "ok",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    gold = gold_mod.GoldStore(tmp_path / "gold")
    assert gold.count("course-map") == 1


def test_corrupt_registry_loads_empty(tmp_path: Path) -> None:
    registry = load_service_module("app.domain.course_adapters.registry")
    path = tmp_path / "registry.json"
    path.write_text("{not json", encoding="utf-8")
    assert registry.load_registry(path).entries == {}
    path.write_text("[]", encoding="utf-8")
    assert registry.load_registry(path).entries == {}


def test_harvest_without_gold_root_does_not_fail(tmp_path: Path) -> None:
    pipeline = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline")
    store_mod = load_service_module("app.domain.course_build.store")
    store, user_id, build_id = _filled_build(store_mod, tmp_path)
    pipeline._harvest_course_gold(
        SimpleNamespace(),
        store,
        user_id=user_id,
        build_id=build_id,
    )
    pipeline._harvest_course_gold(
        SimpleNamespace(course_gold_root=""),
        store,
        user_id=user_id,
        build_id=build_id,
    )


def test_product_course_skips_gold_harvest_by_default(tmp_path: Path) -> None:
    pipeline = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline")
    store_mod = load_service_module("app.domain.course_build.store")
    store, user_id, build_id = _filled_build(store_mod, tmp_path)
    gold_root = tmp_path / "gold"
    pipeline._harvest_course_gold(
        SimpleNamespace(course_gold_root=gold_root),
        store,
        user_id=user_id,
        build_id=build_id,
    )
    assert not gold_root.exists()


def test_pipeline_harvest_writes_gold_then_discard_removes_temps(tmp_path: Path) -> None:
    pipeline = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline")
    gold_mod = load_service_module("app.domain.course_adapters.gold")
    store_mod = load_service_module("app.domain.course_build.store")
    checkpoint = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_checkpoint"
    )
    store, user_id, build_id = _filled_build(store_mod, tmp_path)
    gold_root = tmp_path / "gold"
    pipeline._harvest_course_gold(
        SimpleNamespace(course_gold_root=gold_root, course_gold_harvest=True),
        store,
        user_id=user_id,
        build_id=build_id,
    )
    gold = gold_mod.GoldStore(gold_root)
    assert gold.count("course-map") == 1
    checkpoint.mark_build_done(store, user_id=user_id, build_id=build_id)
    assert store.exists(user_id, build_id)
    store.discard(user_id, build_id)
    assert not store.exists(user_id, build_id)
    assert gold.count("course-theory") == 2


def test_harvest_quizzes_without_theory_skips_quiz_gold(tmp_path: Path) -> None:
    gold_mod = load_service_module("app.domain.course_adapters.gold")
    store_mod = load_service_module("app.domain.course_build.store")
    store = store_mod.CourseBuildStore(tmp_path / "builds", ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "FastAPI", "locale": "en"},
        title="FastAPI",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    store.save_topic(
        user_id,
        build_id,
        "t1",
        quizzes=[_usable_quiz("FastAPI builds JSON APIs with type hints.")],
        codes=[],
    )
    gold = gold_mod.GoldStore(tmp_path / "gold")
    written = gold_mod.harvest_from_build(store, gold, user_id=user_id, build_id=build_id)
    assert written == 0
    assert gold.count("course-quiz") == 0
    assert gold.count("course-theory") == 0


def test_single_chapter_does_not_write_map_gold(tmp_path: Path) -> None:
    gold_mod = load_service_module("app.domain.course_adapters.gold")
    store_mod = load_service_module("app.domain.course_build.store")
    store = store_mod.CourseBuildStore(tmp_path / "builds", ttl_days=30)
    user_id = uuid.uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload={"title": "One"},
        title="One",
        mode="topic_bundles",
    )
    build_id = uuid.UUID(meta.build_id)
    store.save_compiler(
        user_id,
        build_id,
        {
            "chapters": [
                {
                    "id": "t1",
                    "title": "Only chapter",
                    "objective": "One idea",
                    "source_excerpt": "Short excerpt about one idea.",
                }
            ]
        },
    )
    gold = gold_mod.GoldStore(tmp_path / "gold")
    written = gold_mod.harvest_from_build(store, gold, user_id=user_id, build_id=build_id)
    assert written == 0
    assert gold.count("course-map") == 0


def test_report_roundtrip_json() -> None:
    evaluate = load_service_module("app.domain.course_adapters.evaluate")
    original = _report(evaluate, _score(evaluate, coverage=0.7, quiz=0.6, practice=0.5), n=20)
    restored = evaluate.report_from_dict(original.to_dict())
    assert restored.article_count == 20
    assert restored.mean == pytest.approx(original.mean)
