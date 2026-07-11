from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StudioValidationIssue(BaseModel):
    path: str
    message: str


class StudioValidateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    manifest: dict[str, object]


class StudioValidateResponse(BaseModel):
    valid: bool
    errors: list[StudioValidationIssue]


class StudioAsset(BaseModel):
    model_config = ConfigDict(strict=True)

    path: str = Field(min_length=1)
    content_base64: str = Field(min_length=1)


class StudioBuildRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    manifest: dict[str, object]
    assets: list[StudioAsset] = Field(default_factory=list)


class StudioSuggestRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    context: str = Field(min_length=1)
    step_kind: str = "lab"
    prompt: str = Field(min_length=1)
    manifest_fragment: dict[str, object] | None = None


class StudioSuggestResponse(BaseModel):
    suggestion: dict[str, object]
