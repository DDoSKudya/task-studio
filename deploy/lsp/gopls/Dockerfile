FROM golang:1.23-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && go install golang.org/x/tools/gopls@v0.18.1 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/go/bin:${PATH}"

EXPOSE 3000

CMD ["socat", "TCP-LISTEN:3000,reuseaddr,fork", "EXEC:gopls"]
