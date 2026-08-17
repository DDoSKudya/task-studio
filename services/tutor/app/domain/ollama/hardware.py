from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal

OllamaHwProfile = Literal["cpu-light", "cpu-balanced", "gpu-light", "gpu-balanced"]


@dataclass(frozen=True, slots=True)
class HostHardware:
    gpu_available: bool
    gpu_vram_gb: float | None
    system_ram_gb: float | None
    source: str


def _env_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _env_bool(name: str) -> bool | None:
    raw = os.getenv(name, "").strip().casefold()
    if not raw:
        return None
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def detect_system_ram_gb() -> float | None:
    env_value = _env_float("OLLAMA_SYSTEM_RAM_GB")
    if env_value is not None:
        return env_value
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return float(parts[1]) / (1024 * 1024)
    except OSError:
        pass
    page_size = getattr(os, "sysconf", None)
    if page_size is None:
        return None
    try:
        bytes_total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None
    if bytes_total <= 0:
        return None
    return bytes_total / (1024**3)


def detect_gpu_vram_gb() -> float | None:
    env_value = _env_float("OLLAMA_GPU_VRAM_GB")
    if env_value is not None:
        return env_value
    if not shutil.which("nvidia-smi"):
        return None
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    totals: list[float] = []
    for line in completed.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            totals.append(float(raw) / 1024.0)
        except ValueError:
            continue
    return max(totals) if totals else None


def detect_gpu_available() -> bool:
    forced = _env_bool("OLLAMA_GPU_AVAILABLE")
    if forced is not None:
        return forced
    if detect_gpu_vram_gb() is not None:
        return True
    if not shutil.which("nvidia-smi"):
        return False
    try:
        completed = subprocess.run(
            ["nvidia-smi", "-L"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and bool(completed.stdout.strip())


def probe_host_hardware() -> HostHardware:
    gpu = detect_gpu_available()
    vram = detect_gpu_vram_gb() if gpu else None
    ram = detect_system_ram_gb()
    sources: list[str] = []
    if os.getenv("OLLAMA_GPU_AVAILABLE") or os.getenv("OLLAMA_GPU_VRAM_GB"):
        sources.append("env-gpu")
    elif gpu:
        sources.append("probe-gpu")
    if os.getenv("OLLAMA_SYSTEM_RAM_GB"):
        sources.append("env-ram")
    elif ram is not None:
        sources.append("probe-ram")
    return HostHardware(
        gpu_available=gpu,
        gpu_vram_gb=vram,
        system_ram_gb=ram,
        source="+".join(sources) or "defaults",
    )


def recommend_course_model(hardware: HostHardware) -> str:

    if hardware.gpu_available:
        vram = hardware.gpu_vram_gb
        if vram is not None and vram < 4:
            return "qwen2.5:3b"
        return "qwen2.5:7b"
    return "qwen2.5:3b"


def recommend_chat_model(hardware: HostHardware) -> str:
    if hardware.gpu_available:
        vram = hardware.gpu_vram_gb
        if vram is not None and vram >= 10:
            return "qwen2.5:7b"
        return "qwen2.5:7b"
    ram = hardware.system_ram_gb
    if ram is not None and ram <= 8:
        return "qwen2.5:1.5b"
    return "qwen2.5:3b"


def recommend_profile(hardware: HostHardware) -> OllamaHwProfile:
    if hardware.gpu_available:
        vram = hardware.gpu_vram_gb
        if vram is not None and vram < 10:
            return "gpu-light"
        return "gpu-balanced"
    ram = hardware.system_ram_gb
    if ram is not None and ram <= 8:
        return "cpu-light"
    return "cpu-balanced"
