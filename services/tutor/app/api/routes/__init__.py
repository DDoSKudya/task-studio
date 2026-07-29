from __future__ import annotations

from fastapi import APIRouter

from .learner import router as learner_router
from .learner_llm import router as learner_llm_router
from .studio import router as studio_router

router = APIRouter()
router.include_router(learner_router)
router.include_router(learner_llm_router)
router.include_router(studio_router)
