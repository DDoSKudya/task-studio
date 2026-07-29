from __future__ import annotations

from app.config import StudioApiSettings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream
from studio_contracts.analytics_schemas import (
    AttemptsTimelineResponse,
    ProgressResponse,
    SkipsResponse,
)


async def proxy_analytics[T: ProgressResponse | SkipsResponse | AttemptsTimelineResponse](
    client: UpstreamClient,
    settings: StudioApiSettings,
    user_id: UserId,
    path: str,
    model: type[T],
    params: dict[str, str | int] | None = None,
) -> T:
    upstream = await call_service(
        client,
        settings.analytics_service_url,
        "get",
        path,
        user_id=user_id,
        params=params,
    )
    return parse_upstream(upstream, model)
