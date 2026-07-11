FROM node:20-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && npm install -g typescript typescript-language-server \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 3000

CMD ["socat", "TCP-LISTEN:3000,reuseaddr,fork", "EXEC:typescript-language-server --stdio"]
