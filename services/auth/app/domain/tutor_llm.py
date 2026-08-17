from __future__ import annotations

from app.infra.models import User, UserSetting
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.orchestrator_schemas import TutorLlmSummaryResponse


async def summarize_tutor_llm(session: AsyncSession) -> TutorLlmSummaryResponse:
    total = await session.scalar(select(func.count()).select_from(User)) or 0
    if total == 0:
        return TutorLlmSummaryResponse(
            user_count=0,
            local_fallback_users=0,
            all_external=True,
        )

    external_count = await session.scalar(
        select(func.count(func.distinct(UserSetting.user_id))).where(
            UserSetting.key == "tutor",
            UserSetting.value["provider_url"].astext.is_not(None),
            UserSetting.value["provider_url"].astext != "",
        )
    )
    local_fallback_users = int(total) - int(external_count or 0)

    return TutorLlmSummaryResponse(
        user_count=int(total),
        local_fallback_users=local_fallback_users,
        all_external=local_fallback_users == 0,
    )
