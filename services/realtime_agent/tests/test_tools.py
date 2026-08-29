import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services_client import ServicesClient, generate_service_token
from voice_tools import (
    NAVIGATION_TARGETS,
    _ask_agent_impl,
    _open_navigation_impl,
    _respond_to_approval_impl,
    build_tools,
)


def test_generate_service_token():
    token = generate_service_token(user_id="42", workspace_id="100", role="founder")
    assert token is not None
    assert isinstance(token, str)


def test_open_navigation_valid_targets():
    publish_mock = MagicMock()
    for target in NAVIGATION_TARGETS:
        res = _open_navigation_impl(publish_mock, target, "Test Project")
        assert res == {"ok": True}
        publish_mock.assert_called_with(target, "Test Project")


def test_open_navigation_invalid_target():
    publish_mock = MagicMock()
    res = _open_navigation_impl(publish_mock, "invalid_screen", None)
    assert res["ok"] is False
    assert "target không hợp lệ" in res["error"]
    publish_mock.assert_not_called()


@pytest.mark.asyncio
async def test_ask_agent_impl_delegates_to_services_client():
    client = MagicMock(spec=ServicesClient)
    client.execute_agent_turn = AsyncMock(
        return_value={"run_id": "run-123", "output": "CEO Brief: healthy", "approval_required": False}
    )

    result = await _ask_agent_impl(
        conversation_id="conv-1",
        query="Cho tôi xem CEO brief",
        workspace_id=123,
        user_id=456,
        client=client,
    )

    client.execute_agent_turn.assert_awaited_once_with(
        conversation_id="conv-1",
        content="Cho tôi xem CEO brief",
        workspace_id=123,
        user_id=456,
    )
    assert result["run_id"] == "run-123"
    assert result["output"] == "CEO Brief: healthy"


@pytest.mark.asyncio
async def test_respond_to_approval_impl_delegates_to_services_client():
    client = MagicMock(spec=ServicesClient)
    client.decide_approval = AsyncMock(
        return_value={"approval_id": "app-1", "status": "APPROVED"}
    )

    result = await _respond_to_approval_impl(
        approval_id="app-1",
        approved=True,
        reason="Tôi đồng ý",
        workspace_id=123,
        user_id=456,
        client=client,
    )

    client.decide_approval.assert_awaited_once_with(
        approval_id="app-1",
        approved=True,
        reason="Tôi đồng ý",
        workspace_id=123,
        user_id=456,
    )
    assert result["status"] == "APPROVED"


def test_build_tools_returns_voice_tools():
    tools = build_tools(room=None, workspace_id=10, user_id=20, conversation_id="conv-xyz")
    names = [getattr(t, "__name__", str(t)) for t in tools]
    # Check that tools are function tools for voice interaction
    assert len(tools) == 3
