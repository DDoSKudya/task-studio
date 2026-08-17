from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_python_article_with_yazyk_is_programming() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )
    detected = profile.detect_course_profile(
        title="Язык программирования Python и FastAPI",
        corpus="def path_operation():\n    from fastapi import FastAPI\n",
    )
    assert detected == "programming"
    assert profile.practice_needs_code_starter(detected) is True
    assert profile.course_family(detected) == "technical"


def test_product_name_alone_does_not_select_course_profile() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )

    detected = profile.detect_course_profile(
        title="FastAPI",
        corpus="FastAPI",
    )

    assert detected == "general"


def test_ielts_article_is_language_learning() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )
    detected = profile.detect_course_profile(
        title="IELTS Academic Writing",
        corpus="Prepare for IELTS: vocabulary, grammar, and English essay structure.",
    )
    assert detected == "language_learning"
    assert profile.practice_needs_code_starter(detected) is False
    assert profile.profile_skill_overlay(detected) == "domain-language-learning"


def test_history_article_is_humanities() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )
    detected = profile.detect_course_profile(
        title="История культуры Серебряного века",
        corpus="Философия и литература эпохи. Гуманитарное чтение поэмы.",
    )
    assert detected == "humanities"
    assert profile.course_family(detected) == "humanities"
    assert profile.practice_needs_code_starter(detected) is False


def test_hinted_profile_used_when_detect_is_weak() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )
    asserted = profile.normalize_course_profile(
        "business",
        domain="general",
        title="Untitled",
        corpus="hello world",
    )
    assert asserted == "business"


def test_strong_detect_beats_mismatched_hint() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )
    asserted = profile.normalize_course_profile(
        "business",
        domain="code",
        title="FastAPI path operations",
        corpus="from fastapi import FastAPI\ndef read_item():\n    pass\n",
    )
    assert asserted == "programming"


def test_history_beats_legacy_code_domain() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )
    asserted = profile.normalize_course_profile(
        "",
        domain="code",
        title="История культуры Серебряного века",
        corpus="Философия и литература эпохи. Гуманитарное чтение поэмы.",
    )
    assert asserted == "humanities"


def test_legacy_language_domain_maps_without_general_fallback() -> None:
    profile = load_service_module(
        "app.domain.course_from_article.curriculum.outline.course_profile"
    )
    asserted = profile.normalize_course_profile(
        "",
        domain="language",
        title="Untitled",
        corpus="hello",
    )
    assert asserted == "language_learning"
