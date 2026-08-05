from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

CourseDepth = Literal["light", "standard", "deep"]
CourseLayout = Literal["phased", "by_topic"]
CodeSuitabilityPolicy = Literal["ask", "auto_open", "auto_skip"]
CodeSuitabilityAction = Literal["keep_code", "open_tasks", "no_practice"]
CourseBuildStatus = Literal["running", "paused", "failed", "done"]
CourseLocale = Literal["ru", "en"]


def _coerce_uuid(value: object) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


WireUuid = Annotated[uuid.UUID, BeforeValidator(_coerce_uuid)]


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
    content: str = Field(min_length=40)
    videos: list[CourseArticleVideo] | None = None


class CourseFromArticleRequest(BaseModel):
    model_config = ConfigDict(strict=False)

    article: str | None = None
    articles: list[CourseArticleInput] | None = None
    title: str | None = None
    # Course content language (not UI). Sources may be any language; output follows this.
    locale: CourseLocale = "ru"
    audience: str | None = None
    runtime: str | None = None
    runtime_version: str | None = None
    course_depth: CourseDepth = "standard"
    # phased: all theory → all quizzes → all practice.
    # by_topic: per chapter theory(ies) → quizzes → practice, then next chapter.
    layout: CourseLayout = "by_topic"
    split_long_theory: bool = True
    theory_count: int | None = Field(default=None, ge=1, le=100)
    quiz_count: int = Field(default=6, ge=1, le=100)
    code_count: int = Field(default=3, ge=0, le=12)
    practice_count: int | None = Field(default=None, ge=0, le=12)
    ignore_deviations: bool = False
    include_theory: bool = True
    include_quizzes: bool = True
    include_code: bool = True
    code_suitability_policy: CodeSuitabilityPolicy = "ask"
    code_suitability_action: CodeSuitabilityAction | None = None
    build_id: uuid.UUID | None = None

    def uses_topic_bundles(self) -> bool:
        return self.layout == "by_topic"

    @field_validator("locale", mode="before")
    @classmethod
    def coerce_course_locale(cls, value: object) -> CourseLocale:
        return "en" if str(value or "").strip().casefold().startswith("en") else "ru"

    def effective_quiz_count(self) -> int:
        if self.quiz_count:
            return self.quiz_count
        return {"light": 4, "standard": 6, "deep": 10}[self.course_depth]

    def effective_practice_count(self) -> int:
        if self.practice_count is not None:
            return self.practice_count
        if self.code_count is not None:
            return self.code_count
        return {"light": 1, "standard": 3, "deep": 5}[self.course_depth]

    def effective_theory_count(self) -> int | None:
        if self.theory_count is not None:
            return self.theory_count
        return {"light": 3, "standard": 6, "deep": 10}[self.course_depth]

    @model_validator(mode="after")
    def require_source_content(self) -> CourseFromArticleRequest:
        if self.build_id is not None:
            if not (self.include_theory or self.include_quizzes or self.include_code):
                raise ValueError("at least one content stage required: theory, quizzes, or code")
            return self
        if articles := self.articles or []:
            if len(articles) > 50:
                raise ValueError("at most 50 articles allowed")
        else:
            text = (self.article or "").strip()
            if len(text) < 80:
                raise ValueError("article or articles required (min 80 chars for single article)")
        if not (self.include_theory or self.include_quizzes or self.include_code):
            raise ValueError("at least one content stage required: theory, quizzes, or code")
        return self


class CourseBuildSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    build_id: WireUuid
    title: str
    status: CourseBuildStatus
    stage: str
    progress: float = Field(ge=0.0, le=1.0)
    message: str = ""
    chapter_total: int = 0
    chapters_done: int = 0
    error: str | None = None
    created_at: str
    updated_at: str
    mode: str = "topic_bundles"


class CourseBuildDetail(CourseBuildSummary):
    """Сводка + сохранённый запрос (статьи/опции) для возобновления в UI."""

    request: dict[str, object] = Field(default_factory=dict)


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


class FetchArticlesFromUrlsRequest(BaseModel):
    """Batch article ingest. Prefer ``urls``; ``text`` may contain many pasted links."""

    model_config = ConfigDict(strict=False)

    urls: list[str] = Field(default_factory=list, max_length=20)
    text: str | None = Field(default=None, max_length=20_000)


class FetchArticleBatchItem(BaseModel):
    model_config = ConfigDict(strict=True)

    url: str
    ok: bool
    index: int = 0
    title: str | None = None
    content: str | None = None
    source_url: str | None = None
    videos: list[CourseArticleVideo] = Field(default_factory=list)
    error: str | None = None


class FetchArticlesFromUrlsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    results: list[FetchArticleBatchItem] = Field(default_factory=list)
    total: int = 0
    ok_count: int = 0
    error_count: int = 0
