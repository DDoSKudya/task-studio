# syntax=docker/dockerfile:1.7
# Build from repository root: docker build -f services/catalog/Dockerfile .
FROM python:3.12.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8002 \
    HOST=0.0.0.0

WORKDIR /app

RUN useradd -m -u 10001 appuser

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY packages/python-common packages/python-common
COPY packages/contracts packages/contracts
COPY services/catalog services/catalog

# Strip CR so Windows checkout (core.autocrlf) cannot break the entrypoint shebang.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package studio-catalog --no-dev --frozen \
 && sed -i 's/\r$//' /app/services/catalog/docker-entrypoint.sh \
 && chmod +x /app/services/catalog/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/services/catalog
# Root: Docker Desktop bind-mounts for data/packs are often not writable by uid 10001.
USER root

EXPOSE 8002

HEALTHCHECK --interval=10s --timeout=5s --retries=18 --start-period=120s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8002'), timeout=4)"

# Explicit sh: ignores broken +x/shebang after CRLF checkout mistakes.
ENTRYPOINT ["/bin/sh", "/app/services/catalog/docker-entrypoint.sh"]
