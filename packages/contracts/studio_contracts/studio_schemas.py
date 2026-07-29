from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class CourseArticleVideo(BaseModel):
    model_config = ConfigDict(strict=False)

    url: str = Field(min_length=8, max_length=2048)
    title: str | None = None


class CourseArticleInput(BaseModel):
    model_config = ConfigDict(strict=False)

    title: str | None = None
    content: str = Field(min_length=40, max_length=80_000)
    videos: list[CourseArticleVideo] | None = None


class CourseFromArticleRequest(BaseModel):
    model_config = ConfigDict(strict=False)

                                                                                    
    article: str | None = Field(default=None, max_length=120_000)
    articles: list[CourseArticleInput] | None = None
    title: str | None = None
    locale: str = "ru"
    audience: str | None = None
    runtime: str = "python"
    runtime_version: str = "3.12"
    quiz_count: int = Field(default=6, ge=3, le=12)
    code_count: int = Field(default=3, ge=3, le=5)
    ignore_deviations: bool = False
    include_theory: bool = True
    include_quizzes: bool = True
    include_code: bool = True

    @model_validator(mode="after")
    def require_source_content(self) -> CourseFromArticleRequest:
        if articles := self.articles or []:
            if len(articles) > 6:
                raise ValueError("at most 6 articles allowed")
        else:
            text = (self.article or "").strip()
            if len(text) < 80:
                raise ValueError("article or articles required (min 80 chars for single article)")
        if not (self.include_theory or self.include_quizzes or self.include_code):
            raise ValueError("at least one content stage required: theory, quizzes, or code")
        return self


class CourseDeviation(BaseModel):
    model_config = ConfigDict(strict=True)

    summary: str
    sources: list[str] = Field(default_factory=list)


class CourseFromArticleMeta(BaseModel):
    model_config = ConfigDict(strict=True)

    outcomes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    chapters: list[str] = Field(default_factory=list)
    deviations: list[CourseDeviation] = Field(default_factory=list)
    article_count: int = 1


class CourseFromArticleResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    manifest: dict[str, object]
    meta: CourseFromArticleMeta = Field(default_factory=CourseFromArticleMeta)


class FetchArticleFromUrlRequest(BaseModel):
    model_config = ConfigDict(strict=False)

    url: str = Field(min_length=8, max_length=2048)


class FetchArticleFromUrlResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str
    content: str
    source_url: str
    videos: list[CourseArticleVideo] = Field(default_factory=list)
