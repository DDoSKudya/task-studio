FROM golang:1.22-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && go install github.com/sqls-server/sqls@v0.2.28 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/go/bin:${PATH}"

EXPOSE 3000

CMD ["socat", "TCP-LISTEN:3000,reuseaddr,fork", "EXEC:sqls"]
