from __future__ import annotations

from app.api.routes import router as routes_router
from fastapi import APIRouter

router = APIRouter(prefix="/internal/v1/tutor", tags=["tutor"])
router.include_router(routes_router)
