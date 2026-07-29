from __future__ import annotations

from app.api.routes.ingest import router as ingest_router
from app.api.routes.packs import router as packs_router
from fastapi import APIRouter

router = APIRouter(prefix="/internal/v1/catalog", tags=["catalog"])
router.include_router(ingest_router)
router.include_router(packs_router)
