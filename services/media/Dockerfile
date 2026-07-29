# syntax=docker/dockerfile:1.7
# Build from repository root: docker build -f services/media/Dockerfile .
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8009

WORKDIR /app

RUN useradd -m -u 10001 appuser

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY packages/python-common packages/python-common
COPY services/media services/media

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package studio-media --no-dev --frozen

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0
WORKDIR /app/services/media
USER appuser

EXPOSE 8009

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ['PORT'])"

CMD ["sh", "-c", "exec uvicorn app.main:app --host \"${HOST}\" --port \"${PORT}\""]
