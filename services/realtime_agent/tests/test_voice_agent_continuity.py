import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import _parse_room_name, _resolve_conversation_id
from services_client import ServicesClient


def test_parse_room_name():
    w_id, u_id = _parse_room_name("cosa-10-20-123456")
    assert w_id == 10
    assert u_id == 20


@pytest.mark.asyncio
async def test_resolve_conversation_id_from_metadata():
    ctx = MagicMock()
    ctx.room.metadata = json.dumps({"conversation_id": "conv-existing-123"})
    client = MagicMock(spec=ServicesClient)

    conv_id = await _resolve_conversation_id(ctx, 10, 20, client)
    assert conv_id == "conv-existing-123"
    client.create_conversation.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_conversation_id_fallback_creates_new_conversation():
    ctx = MagicMock()
    ctx.room.metadata = ""
    ctx.job.metadata = ""
    client = MagicMock(spec=ServicesClient)
    client.create_conversation = AsyncMock(return_value={"id": "conv-new-789"})

    conv_id = await _resolve_conversation_id(ctx, 10, 20, client)
    assert conv_id == "conv-new-789"
    client.create_conversation.assert_awaited_once_with(
        workspace_id=10,
        user_id=20,
        title="Voice Conversation",
        active_agent_profile="founder_assistant",
    )


@pytest.mark.asyncio
async def test_services_client_send_message():
    client = ServicesClient(base_url="http://fake-agentos:8000")
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"run_id": "run-abc", "status": "RUNNING"}
        res = await client.send_message(
            conversation_id="conv-1",
            content="Hello from voice",
            workspace_id=10,
            user_id=20,
            role="user",
        )
        assert res["run_id"] == "run-abc"
        mock_req.assert_awaited_once_with(
            "POST",
            "/agent/conversations/conv-1/messages",
            workspace_id=10,
            user_id=20,
            json={"content": "Hello from voice", "role": "user"},
            correlation_id=None,
        )


@pytest.mark.asyncio
async def test_services_client_decide_approval():
    client = ServicesClient(base_url="http://fake-agentos:8000")
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"approval_id": "app-99", "status": "APPROVED"}
        res = await client.decide_approval(
            approval_id="app-99",
            approved=True,
            reason="Confirmed by voice",
            workspace_id=10,
            user_id=20,
        )
        assert res["status"] == "APPROVED"
        mock_req.assert_awaited_once_with(
            "POST",
            "/agent/approvals/app-99/decision",
            workspace_id=10,
            user_id=20,
            json={"approved": True, "reason": "Confirmed by voice"},
            correlation_id=None,
        )
