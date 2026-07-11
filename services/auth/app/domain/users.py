from __future__ import annotations

import uuid

from app.domain.passwords import hash_password, verify_password
from app.infra.models import User, UserSetting
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_common.auth_schemas import JsonObject


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _setting_value(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        msg = "user setting value must be a JSON object"
        raise ValueError(msg)
    return {str(key): value for key, value in raw.items()}


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    user = User(email=normalize_email(email), password_hash=hash_password(password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise EmailAlreadyRegisteredError from exc
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.email == normalize_email(email)))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return user


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundError()
    return user


async def list_user_settings(session: AsyncSession, user_id: uuid.UUID) -> JsonObject:
    result = await session.execute(select(UserSetting).where(UserSetting.user_id == user_id))
    return {row.key: row.value for row in result.scalars()}


async def upsert_user_settings(
    session: AsyncSession,
    user_id: uuid.UUID,
    updates: JsonObject,
) -> None:
    for key, value in updates.items():
        result = await session.execute(
            select(UserSetting).where(UserSetting.user_id == user_id, UserSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting is None:
            session.add(UserSetting(user_id=user_id, key=key, value=_setting_value(value)))
        else:
            setting.value = _setting_value(value)
