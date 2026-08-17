from __future__ import annotations

from studio_common.lsp.lsp_framing import encode_lsp_message, read_lsp_message


def test_encode_lsp_message_wraps_body() -> None:
    payload = encode_lsp_message('{"jsonrpc":"2.0","id":1}')
    assert payload.startswith(b"Content-Length: ")
    assert b'{"jsonrpc":"2.0","id":1}' in payload


async def test_read_lsp_message_parses_framed_body() -> None:
    import asyncio

    reader = asyncio.StreamReader()
    reader.feed_data(b'Content-Length: 12\r\n\r\n{"ok": true}')
    message = await read_lsp_message(reader)
    assert message == '{"ok": true}'
