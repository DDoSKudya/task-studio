from __future__ import annotations

import uuid

import httpx
from aio_pika.abc import AbstractChannel
from app.config import IntegrationsSettings
from app.domain.jobs import claim_import_job, get_import_job, run_import_job
from app.domain.messaging import publish_pack_index
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_integration_sdk.registry import AdapterModule


async def handle_import_payload(
    payload: dict[str, object],
    *,
    channel: AbstractChannel,
    session_factory: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient,
    settings: IntegrationsSettings,
    adapters: dict[str, AdapterModule],
) -> None:
    job_id = uuid.UUID(str(payload["job_id"]))
    user_id = uuid.UUID(str(payload["user_id"]))
    platform_id = str(payload["platform_id"])
    adapter = adapters.get(platform_id)
    if adapter is None:
        msg = f"unknown platform {platform_id}"
        raise ValueError(msg)

    async with session_factory() as session:
        job = await get_import_job(session, user_id=user_id, job_id=job_id)
        if job.status in {"done", "failed"}:
            return
        if job.status == "pending" and not await claim_import_job(session, job):
            return
        if job.status != "fetching":
                                                                              
            return
        updated = await run_import_job(
            session,
            http_client,
            settings,
            adapter,
            job,
        )
        if updated.pack_version_id is not None:
            await publish_pack_index(
                channel,
                settings,
                user_id=user_id,
                pack_version_id=updated.pack_version_id,
            )
