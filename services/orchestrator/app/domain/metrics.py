from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
import structlog
from studio_contracts.orchestrator_schemas import TutorLlmSummaryResponse

log = structlog.get_logger("orchestrator.metrics")

_MEM_AVAILABLE = re.compile(r"^node_memory_MemAvailable_bytes\s+(\d+)\s*$", re.MULTILINE)
_LOAD_AVERAGE = re.compile(r"^node_load1\s+([\d.]+)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class HostMetrics:
    free_ram_mb: int | None
    load_average: float | None


async def fetch_host_metrics(client: httpx.AsyncClient, node_exporter_url: str) -> HostMetrics:
    try:
        response = await client.get(f"{node_exporter_url}/metrics", timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("node_exporter_unavailable", error=str(exc))
        return HostMetrics(free_ram_mb=None, load_average=None)

    text = response.text
    free_ram_mb = None
    if match := _MEM_AVAILABLE.search(text):
        free_ram_mb = int(int(match.group(1)) / (1024 * 1024))
    load_average = None
    if match := _LOAD_AVERAGE.search(text):
        load_average = float(match.group(1))
    return HostMetrics(free_ram_mb=free_ram_mb, load_average=load_average)


async def fetch_tutor_llm_summary(
    client: httpx.AsyncClient,
    auth_service_url: str,
    *,
    system_token: str,
) -> TutorLlmSummaryResponse | None:
    headers = {"X-System-Token": system_token} if system_token else {}
    try:
        response = await client.get(
            f"{auth_service_url}/internal/v1/auth/tutor-llm/summary",
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("auth_summary_unavailable", error=str(exc))
        return None
    return TutorLlmSummaryResponse.model_validate(response.json())


async def grading_cpu_hot(
    client: httpx.AsyncClient,
    prometheus_url: str,
    *,
    threshold: float,
    pyroscope_url: str,
) -> bool:
    if await _pyroscope_grading_hot(client, pyroscope_url):
        return True
    query = f'sum(rate(container_cpu_usage_seconds_total{{name=~".*grading.*"}}[2m])) > {threshold}'
    return await _prometheus_query_matches(client, prometheus_url, query)


async def _prometheus_query_matches(
    client: httpx.AsyncClient,
    prometheus_url: str,
    query: str,
) -> bool:
    try:
        response = await client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return False
    body = response.json()
    if not isinstance(body, dict):
        return False
    data = body.get("data")
    if not isinstance(data, dict):
        return False
    result = data.get("result")
    return isinstance(result, list) and bool(result)


async def _pyroscope_grading_hot(client: httpx.AsyncClient, pyroscope_url: str) -> bool:
    try:
        response = await client.get(
            f"{pyroscope_url}/api/render",
            params={"query": "grading.cpu", "from": "now-5m", "until": "now"},
            timeout=10.0,
        )
        if response.status_code in {404, 503}:
            return False
        response.raise_for_status()
    except httpx.HTTPError:
        return False
    body = response.json()
    if not isinstance(body, dict):
        return False
    flamebearer = body.get("flamebearer")
    if not isinstance(flamebearer, dict):
        return False
    levels = flamebearer.get("levels")
    return isinstance(levels, list) and bool(levels)
