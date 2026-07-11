# Build from repository root: docker build -f services/analytics/Dockerfile .
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8008

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY packages/python-common packages/python-common
COPY services/analytics services/analytics

RUN uv sync --package studio-analytics --no-dev --frozen || uv sync --package studio-analytics --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0
WORKDIR /app/services/analytics
USER appuser

EXPOSE 8008

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host \"${HOST}\" --port \"${PORT}\""]
