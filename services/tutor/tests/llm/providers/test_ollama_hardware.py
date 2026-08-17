from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_recommend_course_model_stays_on_home_hardware_sizes() -> None:
    hardware = load_service_module("app.domain.ollama.hardware")
    cases = [
        hardware.HostHardware(True, 12.0, 32.0, "test"),
        hardware.HostHardware(True, 8.0, 16.0, "test"),
        hardware.HostHardware(True, 4.0, 16.0, "test"),
        hardware.HostHardware(False, None, 8.0, "test"),
        hardware.HostHardware(False, None, 32.0, "test"),
        hardware.HostHardware(False, None, None, "test"),
    ]
    for snap in cases:
        model = hardware.recommend_course_model(snap)
        assert "1.5b" not in model.casefold()
        assert model in {"qwen2.5:3b", "qwen2.5:7b"}


def test_recommend_course_model_drops_to_3b_on_tight_memory() -> None:
    hardware = load_service_module("app.domain.ollama.hardware")
    tight_ram = hardware.HostHardware(False, None, 8.0, "t")
    tight_vram = hardware.HostHardware(True, 3.0, 8.0, "t")
    assert hardware.recommend_course_model(tight_ram) == "qwen2.5:3b"
    assert hardware.recommend_course_model(tight_vram) == "qwen2.5:3b"


def test_recommend_course_model_by_vram() -> None:
    hardware = load_service_module("app.domain.ollama.hardware")
    assert (
        hardware.recommend_course_model(hardware.HostHardware(True, 12.0, 32.0, "t"))
        == "qwen2.5:7b"
    )
    assert (
        hardware.recommend_course_model(hardware.HostHardware(True, 7.0, 16.0, "t")) == "qwen2.5:7b"
    )
    assert (
        hardware.recommend_course_model(hardware.HostHardware(False, None, 32.0, "t"))
        == "qwen2.5:3b"
    )


def test_load_policy_accepts_env_course_3b(monkeypatch) -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    monkeypatch.setenv("OLLAMA_ACCELERATOR", "gpu")
    monkeypatch.setenv("OLLAMA_PROFILE", "gpu-balanced")
    monkeypatch.setenv("OLLAMA_GPU_AVAILABLE", "1")
    monkeypatch.setenv("OLLAMA_GPU_VRAM_GB", "12")
    monkeypatch.setenv("OLLAMA_MODEL_COURSE", "qwen2.5:3b")
    monkeypatch.setenv("OLLAMA_MODEL_CHAT", "qwen2.5:3b")
    monkeypatch.delenv("OLLAMA_MODEL_POLISH", raising=False)
    policy = runtime.load_ollama_runtime_policy(fallback_model="qwen2.5:3b")
    assert policy.model_course == "qwen2.5:3b"
    assert policy.model_chat == "qwen2.5:3b"
    assert policy.hardware is not None
    assert policy.hardware.gpu_vram_gb == 12.0
