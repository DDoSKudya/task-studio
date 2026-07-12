from __future__ import annotations

import asyncio
import json
from typing import Literal

import httpx


class DockerControl:
    def __init__(self, client: httpx.AsyncClient, *, compose_project: str) -> None:
        self._client = client
        self._compose_project = compose_project

    async def service_running(self, service: str) -> bool:
        containers = await self._list_service_containers(service)
        if not containers:
            return False
        return any(item.get("State") == "running" for item in containers)

    async def start_service(self, service: str) -> bool:
        return await self._mutate_containers(service, action="start")

    async def stop_service(self, service: str) -> bool:
        return await self._mutate_containers(service, action="stop")

    async def _mutate_containers(self, service: str, *, action: Literal["start", "stop"]) -> bool:
        changed = False
        for container_id in await self._container_ids(service):
            response = await self._client.post(f"/v1.44/containers/{container_id}/{action}")
            if response.status_code in {204, 304}:
                changed = True
        return changed

    async def managed_status(self, services: tuple[str, ...]) -> dict[str, bool]:
        running = await asyncio.gather(*(self.service_running(service) for service in services))
        return dict(zip(services, running, strict=True))

    async def _container_ids(self, service: str) -> list[str]:
        containers = await self._list_service_containers(service)
        return [str(item["Id"]) for item in containers if "Id" in item]

    async def _list_service_containers(self, service: str) -> list[dict[str, object]]:
        filters = json.dumps(
            {
                "label": [
                    f"com.docker.compose.project={self._compose_project}",
                    f"com.docker.compose.service={service}",
                ]
            }
        )
        response = await self._client.get(
            "/v1.44/containers/json",
            params={"all": "true", "filters": filters},
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            return []
        return [item for item in body if isinstance(item, dict)]


def docker_client(socket_path: str) -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport(uds=socket_path)
    return httpx.AsyncClient(transport=transport, base_url="http://docker", timeout=30.0)
