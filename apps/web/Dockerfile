# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS build

WORKDIR /app/apps/web

RUN apk add --no-cache libc6-compat

COPY apps/web/package.json apps/web/package-lock.json ./
COPY packages/editor-core /app/packages/editor-core

# editor-core is a file: link; install its deps under packages/ so Vite can resolve
# imports from /app/packages/editor-core/src (walks that tree, not apps/web/node_modules).
RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts \
 && npm install --prefix /app/packages/editor-core --ignore-scripts --omit=dev --no-package-lock

COPY apps/web/ .
RUN npm run postinstall
ENV NUXT_TYPE_CHECK=false
ENV NUXT_DEVTOOLS=false
ENV NUXT_SKIP_ESLINT=true
ENV NUXT_TELEMETRY_DISABLED=1
ENV NUXT_SOURCEMAP=false
ENV NODE_OPTIONS=--max-old-space-size=2048
# Vite default cacheDir is node_modules/.vite (not .cache).
RUN --mount=type=cache,target=/app/apps/web/node_modules/.vite \
    --mount=type=cache,target=/app/apps/web/node_modules/.cache \
    npm run build

FROM node:22-alpine

WORKDIR /app

RUN apk add --no-cache wget \
    && adduser -D -u 10001 appuser

COPY --from=build --chown=appuser:appuser /app/apps/web/.output ./.output

USER appuser

ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", ".output/server/index.mjs"]
