from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.domain.ollama.runtime_policy import OllamaRuntimePolicy, load_ollama_runtime_policy


@dataclass(frozen=True, slots=True)
class TutorConfig:
    auth_service_url: str
    sessions_service_url: str
    ollama_url: str
    ollama_model: str
    default_provider_url: str
    rate_limit_per_minute: int
    secrets_master_key: str | None
    ollama_runtime: OllamaRuntimePolicy
    course_topic_bundles: bool
    course_builds_root: Path
    course_build_ttl_days: int
    course_gold_root: Path
    course_adapter_registry: Path
    article_fetch_reader_url: str
    course_web_glossary: bool
    course_web_allowlist: tuple[str, ...]


def load_config() -> TutorConfig:
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    topic_bundles = os.getenv("COURSE_TOPIC_BUNDLES", "true").strip().casefold() not in {
        "0",
        "false",
        "no",
    }
    ttl_raw = os.getenv("COURSE_BUILD_TTL_DAYS", "30").strip()
    try:
        ttl_days = max(1, int(ttl_raw))
    except ValueError:
        ttl_days = 30
    web_glossary = os.getenv("COURSE_WEB_GLOSSARY", "").strip().casefold() not in {
        "",
        "0",
        "false",
        "no",
    }
    from app.domain.course_from_article.local_course.integrations.web_glossary import (
        parse_host_allowlist,
    )

    web_allowlist = parse_host_allowlist(os.getenv("COURSE_WEB_ALLOWLIST", ""))
    return TutorConfig(
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth:8001").rstrip("/"),
        sessions_service_url=os.getenv("SESSIONS_SERVICE_URL", "http://sessions:8003").rstrip("/"),
        ollama_url=os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/"),
        ollama_model=ollama_model,
        default_provider_url=os.getenv("TUTOR_DEFAULT_PROVIDER_URL", "").rstrip("/"),
        rate_limit_per_minute=int(os.getenv("TUTOR_RATE_LIMIT_PER_MINUTE", "30")),
        secrets_master_key=os.getenv("SECRETS_MASTER_KEY"),
        ollama_runtime=load_ollama_runtime_policy(fallback_model=ollama_model),
        course_topic_bundles=topic_bundles,
        course_builds_root=Path(os.getenv("COURSE_BUILDS_ROOT", "/data/course-builds")),
        course_build_ttl_days=ttl_days,
        course_gold_root=Path(os.getenv("COURSE_ADAPTER_GOLD_ROOT", "/data/course-gold")),
        course_adapter_registry=Path(
            os.getenv("COURSE_ADAPTER_REGISTRY", "/data/course-adapters/registry.json")
        ),
        article_fetch_reader_url=os.getenv(
            "ARTICLE_FETCH_READER_URL",
            "https://r.jina.ai",
        ).strip(),
        course_web_glossary=web_glossary,
        course_web_allowlist=web_allowlist,
    )
