from __future__ import annotations

import asyncio


def encode_lsp_message(content: str) -> bytes:
    body = content.encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode()
    return header + body


async def read_lsp_message(reader: asyncio.StreamReader) -> str | None:
    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if not line:
            return None
        decoded = line.decode("utf-8").strip()
        if not decoded:
            break
        key, value = decoded.split(": ", 1)
        headers[key] = value
    length = int(headers["Content-Length"])
    body = await reader.readexactly(length)
    return body.decode("utf-8")
