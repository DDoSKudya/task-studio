from __future__ import annotations

import asyncio

from studio_common.lsp.lsp_framing import encode_lsp_message, read_lsp_message


async def bridge_lsp(websocket, host: str, port: int) -> None:
    reader, writer = await asyncio.open_connection(host, port)

    async def client_to_server() -> None:
        while True:
            message = await websocket.receive_text()
            writer.write(encode_lsp_message(message))
            await writer.drain()

    async def server_to_client() -> None:
        while True:
            message = await read_lsp_message(reader)
            if message is None:
                break
            await websocket.send_text(message)

    try:
        await asyncio.gather(client_to_server(), server_to_client())
    finally:
        writer.close()
        await writer.wait_closed()
