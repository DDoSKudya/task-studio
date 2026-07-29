from __future__ import annotations

import uuid
from pathlib import Path

import httpx
from aio_pika.abc import AbstractChannel
from app.config import GradingSettings
from app.domain.pack.materialize import ensure_local_pack_root
from studio_common.rabbitmq import declare_queue, publish_json
from studio_contracts.catalog_schemas import PackVersionContext


async def fetch_pack_root(
    client: httpx.AsyncClient,
    settings: GradingSettings,
    *,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> str:
    response = await client.get(
        f"{settings.catalog_service_url}/internal/v1/catalog/pack-versions/{pack_version_id}",
        headers={"X-User-Id": str(user_id)},
        timeout=30,
    )
    response.raise_for_status()
    ctx = PackVersionContext.model_validate(response.json())
    disk = Path(ctx.disk_path)
    if disk.is_dir():  # noqa: ASYNC240 — sync path probe before optional hydrate
        return ctx.disk_path
    return await ensure_local_pack_root(
        client,
        settings,
        user_id=user_id,
        pack_id=ctx.pack_id,
        version=ctx.version,
        disk_path=disk,
        object_key=ctx.object_key,
    )


async def publish_lab_job(
    channel: AbstractChannel,
    settings: GradingSettings,
    *,
    lab_run_id: uuid.UUID,
    attempt_id: uuid.UUID,
    pack_root: str,
    step: dict[str, object],
) -> None:
    await declare_queue(channel, settings.lab_jobs_queue)
    await publish_json(
        channel,
        settings.lab_jobs_queue,
        {
            "lab_run_id": str(lab_run_id),
            "attempt_id": str(attempt_id),
            "pack_root": pack_root,
            "step": step,
        },
    )
