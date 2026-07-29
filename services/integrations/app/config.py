from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class IntegrationsSettings:
    integration_modules_root: Path
    packs_root: Path
    catalog_service_url: str
    auth_service_url: str
    rabbitmq_url: str
    import_queue: str
    search_index_queue: str
    secrets_master_key: str | None


def load_settings() -> IntegrationsSettings:
    root = Path(os.getenv("INTEGRATION_MODULES_ROOT", "/app/integration_modules"))
    packs = Path(os.getenv("PACKS_ROOT", "/data/packs"))
    master = os.getenv("SECRETS_MASTER_KEY", "").strip()
    return IntegrationsSettings(
        integration_modules_root=root,
        packs_root=packs,
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth:8001").rstrip("/"),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "").strip(),
        import_queue=os.getenv("IMPORT_QUEUE", "import.jobs"),
        search_index_queue=os.getenv("SEARCH_INDEX_QUEUE", "search.index"),
        secrets_master_key=master or None,
    )
