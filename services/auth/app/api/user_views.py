from __future__ import annotations

import uuid

from app.domain.users import UserNotFoundError, get_user_by_id, list_user_settings
from app.infra.models import User
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from studio_common.security.auth_schemas import AuthSuccess, MeResponse, UserProfile


async def user_or_404(session: AsyncSession, user_id: uuid.UUID) -> User:
    try:
        return await get_user_by_id(session, user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") from exc


def auth_success(user: User) -> AuthSuccess:
    return AuthSuccess(user=UserProfile.model_validate(user))


async def me_from_user(session: AsyncSession, user: User) -> MeResponse:
    settings = await list_user_settings(session, user.id)
    return MeResponse(user=UserProfile.model_validate(user), settings=settings)
