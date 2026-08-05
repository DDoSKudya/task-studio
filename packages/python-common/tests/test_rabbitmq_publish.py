from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from studio_common.rabbitmq import publish_json


@pytest.mark.asyncio
async def test_publish_json_sets_message_id() -> None:
    channel = MagicMock()
    channel.default_exchange.publish = AsyncMock()
    await publish_json(channel, "q", {"a": 1}, message_id="fixed-id")
    call = channel.default_exchange.publish.await_args
    assert call is not None
    message = call.args[0]
    assert call.kwargs["routing_key"] == "q"
    assert message.message_id == "fixed-id"


@pytest.mark.asyncio
async def test_publish_json_generates_message_id_when_missing() -> None:
    channel = MagicMock()
    channel.default_exchange.publish = AsyncMock()
    await publish_json(channel, "q", {"a": 1})
    call = channel.default_exchange.publish.await_args
    assert call is not None
    message = call.args[0]
    assert message.message_id is not None
    uuid.UUID(str(message.message_id))
