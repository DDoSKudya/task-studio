from typing import cast

from studio_contracts.packs.pack_content import content_modules_from_manifest


def test_content_modules_from_empty_manifest() -> None:
    assert content_modules_from_manifest(None) == content_modules_from_manifest({})
    assert content_modules_from_manifest({"topics": []}) == content_modules_from_manifest({})


def test_content_modules_detects_step_kinds() -> None:
    manifest = cast(
        dict[str, object],
        {
            "steps": {
                "s1": {"kind": "theory", "title": "Intro"},
                "s2": {"kind": "video", "title": "Clip"},
                "s3": {"kind": "quiz", "title": "Check"},
                "s4": {"kind": "code", "title": "Task"},
                "s5": {"kind": "lab", "title": "Lab"},
                "s6": {"kind": "task", "title": "Open"},
            }
        },
    )
    modules = content_modules_from_manifest(manifest)
    assert modules.has_theory is True
    assert modules.has_video is True
    assert modules.has_quiz is True
    assert modules.has_practice is True


def test_content_modules_video_only() -> None:
    manifest = cast(
        dict[str, object],
        {
            "steps": {
                "s1": {"kind": "video", "title": "Clip"},
            }
        },
    )
    modules = content_modules_from_manifest(manifest)
    assert modules.has_theory is False
    assert modules.has_video is True


def test_content_modules_partial_course() -> None:
    manifest = cast(
        dict[str, object],
        {
            "steps": {
                "s1": {"kind": "theory", "title": "Only theory"},
            }
        },
    )
    modules = content_modules_from_manifest(manifest)
    assert modules.has_theory is True
    assert modules.has_quiz is False
    assert modules.has_practice is False
