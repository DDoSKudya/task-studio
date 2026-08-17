from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from studio_contracts.api.integration_schemas import AdapterInfo


@dataclass(frozen=True, slots=True)
class AdapterModule:
    info: AdapterInfo
    health: Callable[[], dict[str, object]]
    list_catalog: Callable[..., list[dict[str, object]]]
    import_course: Callable[..., tuple[dict[str, object], dict[str, object]]]
    search_remote: Callable[..., list[dict[str, object]]]
    enroll: Callable[..., dict[str, object]] | None = None
