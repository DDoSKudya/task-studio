from __future__ import annotations

from app.api.deps import DbSession, SystemAuth, UserId
from app.api.user_views import auth_success, me_from_user, user_or_404
from app.domain.tutor_llm import summarize_tutor_llm
from app.domain.users import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
    upsert_user_settings,
)
from fastapi import APIRouter, HTTPException, status
from studio_common.security.auth_schemas import (
    AuthSuccess,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    SettingsPatch,
)
from studio_contracts.api.orchestrator_schemas import TutorLlmSummaryResponse

router = APIRouter(prefix="/internal/v1/auth", tags=["auth"])


@router.get("/tutor-llm/summary", response_model=TutorLlmSummaryResponse)
async def tutor_llm_summary(_auth: SystemAuth, session: DbSession) -> TutorLlmSummaryResponse:
    return await summarize_tutor_llm(session)


@router.post("/register", response_model=AuthSuccess, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: DbSession) -> AuthSuccess:
    try:
        user = await register_user(session, body.email, body.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        ) from exc
    return auth_success(user)


@router.post("/login", response_model=AuthSuccess)
async def login(body: LoginRequest, session: DbSession) -> AuthSuccess:
    try:
        user = await authenticate_user(session, body.email, body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        ) from exc
    return auth_success(user)


@router.get("/me", response_model=MeResponse)
async def me(user_id: UserId, session: DbSession) -> MeResponse:
    user = await user_or_404(session, user_id)
    return await me_from_user(session, user)


@router.patch("/me/settings", response_model=MeResponse)
async def patch_settings(body: SettingsPatch, user_id: UserId, session: DbSession) -> MeResponse:
    user = await user_or_404(session, user_id)

    if body.locale is not None:
        user.locale = body.locale
    if body.theme is not None:
        user.theme = body.theme
    if body.settings is not None:
        await upsert_user_settings(session, user_id, body.settings)
    await session.commit()
    return await me_from_user(session, user)
