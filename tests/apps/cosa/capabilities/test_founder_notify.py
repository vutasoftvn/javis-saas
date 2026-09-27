"""Capability `founder.notify.send` (ADR-FOUNDER-CHANNEL-001, plan hub đợt 2 B2).

Schema tool không có tham số người nhận; handler chỉ gửi `content`/`channelKind` tới
company. Người nhận do company tự tra theo danh tính trong delegation của run.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.governance.contracts import ApprovalPolicy

from apps.cosa.capabilities.founder_notify import (
    FOUNDER_NOTIFY_SEND_SPEC,
    create_founder_notify_send_handler,
)
from apps.cosa.capabilities.okr_write import OKR_KEY_RESULT_CREATE_SPEC

CTX = {"workspace_id": "ws-1", "locale": "vi-VN"}
PATH = "/identity/founder-notifications/send"


def test_spec_has_no_recipient_parameter_and_matches_t2_policy() -> None:
    spec = FOUNDER_NOTIFY_SEND_SPEC
    assert spec.id == "founder.notify.send"
    assert spec.risk is OKR_KEY_RESULT_CREATE_SPEC.risk
    assert spec.approval_policy is OKR_KEY_RESULT_CREATE_SPEC.approval_policy
    assert spec.approval_policy is ApprovalPolicy.POLICY_DRIVEN
    assert spec.input_schema == {
        "type": "object",
        "required": ["content"],
        "additionalProperties": False,
        "properties": {
            "content": {"type": "string", "minLength": 1, "maxLength": 4000},
            "channel_kind": {"type": "string", "enum": ["telegram"]},
        },
    }


@pytest.mark.asyncio
async def test_handler_posts_only_content_and_channel_kind() -> None:
    client = AsyncMock()
    client.post.return_value = {
        "delivered": True,
        "channelKind": "telegram",
        "channelLabel": "Nhóm của tôi",
    }
    out = await create_founder_notify_send_handler(client)(
        {"content": "  Tóm tắt email  ", "channel_kind": "telegram"}, CTX
    )

    client.post.assert_awaited_once()
    assert client.post.await_args.args == (PATH,)
    assert client.post.await_args.kwargs == {
        "json": {"content": "Tóm tắt email", "channelKind": "telegram"},
        "headers": {"X-Workspace-Id": "ws-1"},
    }
    assert out == {"delivered": True, "channel_kind": "telegram", "channel_label": "Nhóm của tôi"}


@pytest.mark.asyncio
async def test_handler_omits_channel_kind_when_absent() -> None:
    client = AsyncMock()
    client.post.return_value = {
        "delivered": True,
        "channelKind": "telegram",
        "channelLabel": "Telegram",
    }
    await create_founder_notify_send_handler(client)({"content": "Xin chào"}, CTX)
    assert set(client.post.await_args.kwargs["json"]) == {"content"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field", ["chat_id", "chatId", "recipient", "channel_id", "founder_member_id"]
)
async def test_handler_rejects_recipient_like_arguments(field: str) -> None:
    client = AsyncMock()
    with pytest.raises(ValueError, match=field):
        await create_founder_notify_send_handler(client)({"content": "x", field: "999"}, CTX)
    client.post.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        {"content": "   "},
        {},
        {"content": 12},
        {"content": "a" * 4001},
        {"content": "x", "channel_kind": "sms"},
    ],
)
async def test_handler_rejects_invalid_content_or_kind(args: dict) -> None:
    client = AsyncMock()
    with pytest.raises(ValueError):
        await create_founder_notify_send_handler(client)(args, CTX)
    client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_handler_requires_workspace_from_context() -> None:
    client = AsyncMock()
    with pytest.raises(ValueError, match="workspace_id"):
        await create_founder_notify_send_handler(client)({"content": "x"}, {})
    client.post.assert_not_awaited()
