from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

type JsonObject = dict[str, object]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    locale: str
    theme: str


class AuthSuccess(BaseModel):
    user: UserProfile


class SettingsPatch(BaseModel):
    model_config = ConfigDict(strict=True)

    locale: str | None = Field(default=None, pattern=r"^(en|ru)$")
    theme: str | None = Field(default=None, pattern=r"^(light|dark|system)$")
    settings: JsonObject | None = None


class MeResponse(BaseModel):
    user: UserProfile
    settings: JsonObject
