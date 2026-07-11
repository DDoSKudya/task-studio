from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from app.domain.users import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UserNotFoundError,
    authenticate_user,
    get_user_by_id,
    list_user_settings,
    register_user,
    upsert_user_settings,
)
from app.infra.models import User
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.auth_schemas import (
    AuthSuccess,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    SettingsPatch,
    UserProfile,
)

router = APIRouter(prefix="/internal/v1/auth", tags=["auth"])


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state,
        "db_session_factory",
        None,
    )
    if factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        )
    return factory


async def get_db(
    factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session


def get_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> uuid.UUID:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing user id")
    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid user id",
        ) from exc


type DbSession = Annotated[AsyncSession, Depends(get_db)]
type UserId = Annotated[uuid.UUID, Depends(get_user_id)]


async def _user_or_404(session: AsyncSession, user_id: uuid.UUID) -> User:
    try:
        return await get_user_by_id(session, user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") from exc


def _auth_success(user: User) -> AuthSuccess:
    return AuthSuccess(user=UserProfile.model_validate(user))


async def _me_from_user(session: AsyncSession, user: User) -> MeResponse:
    settings = await list_user_settings(session, user.id)
    return MeResponse(user=UserProfile.model_validate(user), settings=settings)


@router.post("/register", response_model=AuthSuccess, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: DbSession) -> AuthSuccess:
    try:
        user = await register_user(session, body.email, body.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        ) from exc
    return _auth_success(user)


@router.post("/login", response_model=AuthSuccess)
async def login(body: LoginRequest, session: DbSession) -> AuthSuccess:
    try:
        user = await authenticate_user(session, body.email, body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        ) from exc
    return _auth_success(user)


@router.get("/me", response_model=MeResponse)
async def me(user_id: UserId, session: DbSession) -> MeResponse:
    user = await _user_or_404(session, user_id)
    return await _me_from_user(session, user)


@router.patch("/me/settings", response_model=MeResponse)
async def patch_settings(body: SettingsPatch, user_id: UserId, session: DbSession) -> MeResponse:
    user = await _user_or_404(session, user_id)

    if body.locale is not None:
        user.locale = body.locale
    if body.theme is not None:
        user.theme = body.theme
    if body.settings is not None:
        await upsert_user_settings(session, user_id, body.settings)
    await session.commit()
    return await _me_from_user(session, user)
