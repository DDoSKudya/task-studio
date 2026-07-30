from __future__ import annotations

from app.api.deps import Adapters
from fastapi import APIRouter
from studio_contracts.integration_schemas import AdapterInfo

from .catalog import router as catalog_router
from .discover import router as discover_router
from .enroll import router as enroll_router
from .jobs import router as jobs_router

router = APIRouter(prefix="/internal/v1/integrations", tags=["integrations"])


@router.get("", response_model=list[AdapterInfo])
async def list_adapters(adapters: Adapters) -> list[AdapterInfo]:
    return [adapter.info for adapter in adapters.values()]


router.include_router(discover_router)
router.include_router(catalog_router)
router.include_router(enroll_router)
router.include_router(jobs_router)
