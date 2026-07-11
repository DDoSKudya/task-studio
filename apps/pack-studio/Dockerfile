FROM node:22.23-alpine3.22 AS build

WORKDIR /app

RUN apk add --no-cache libc6-compat \
    && apk upgrade --no-cache

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
ARG NUXT_APP_BASE_URL=/pack-studio/
ENV NUXT_APP_BASE_URL=$NUXT_APP_BASE_URL
RUN npm run build

FROM node:22.23-alpine3.22

WORKDIR /app

RUN apk add --no-cache wget \
    && apk upgrade --no-cache \
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
