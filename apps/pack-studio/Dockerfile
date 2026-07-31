# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS build

WORKDIR /app

RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts

COPY . .
ARG NUXT_APP_BASE_URL=/pack-studio/
ENV NUXT_APP_BASE_URL=$NUXT_APP_BASE_URL
RUN npm run postinstall
ENV NUXT_TYPE_CHECK=false
ENV NUXT_DEVTOOLS=false
ENV NUXT_TELEMETRY_DISABLED=1
ENV NUXT_SOURCEMAP=false
ENV NODE_OPTIONS=--max-old-space-size=2048
RUN --mount=type=cache,target=/app/node_modules/.vite \
    --mount=type=cache,target=/app/node_modules/.cache \
    npm run build

FROM node:22-alpine

WORKDIR /app

RUN apk add --no-cache wget \
    && adduser -D -u 10001 appuser

COPY --from=build --chown=appuser:appuser /app/.output ./.output

USER appuser

ENV HOST=0.0.0.0
ENV PORT=3000
ENV NUXT_APP_BASE_URL=/pack-studio/

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3000/pack-studio/health || exit 1

CMD ["node", ".output/server/index.mjs"]
