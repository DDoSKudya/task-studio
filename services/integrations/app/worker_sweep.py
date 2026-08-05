from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.jobs import fail_stale_import_jobs

log = structlog.get_logger("integrations.worker")

_SWEEP_INTERVAL_SEC = 60.0


def start_import_sweeper(
    session_factory: async_sessionmaker[AsyncSession],
) -> asyncio.Task[None]:
    async def _runner() -> None:
        while True:
            try:
                async with session_factory() as session:
                    cleared = await fail_stale_import_jobs(session)
                    if cleared:
                        log.info("stale_import_jobs_cleared", count=cleared)
            except asyncio.CancelledError:
                raise
            except (SQLAlchemyError, OSError, ConnectionError, TimeoutError, RuntimeError):
                log.exception("stale_import_sweep_failed")
            await asyncio.sleep(_SWEEP_INTERVAL_SEC)

    return asyncio.create_task(_runner())
