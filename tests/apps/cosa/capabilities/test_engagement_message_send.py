from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.wait import WaitKind
from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent_core.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
)
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.runs.repository import InMemoryRunRepository
from apps.cosa.capabilities.client import CompanyServiceClient, CompanyServiceError
from apps.cosa.capabilities.engagement_message_send import (
    ENGAGEMENT_MESSAGE_SEND_SPEC,
    create_engagement_message_send_handler,
)


@pytest.fixture
def gateway_setup():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    mock_client = AsyncMock(spec=CompanyServiceClient)
    handler = create_engagement_message_send_handler(mock_client)
    registry.register(ENGAGEMENT_MESSAGE_SEND_SPEC, handler)

    gateway = CapabilityGateway(registry=registry, repository=repo)
    return gateway, repo, mock_client


@pytest.mark.asyncio
async def test_engagement_message_send_spec_metadata():
    assert ENGAGEMENT_MESSAGE_SEND_SPEC.id == "engagement.message.send"
    assert ENGAGEMENT_MESSAGE_SEND_SPEC.risk == CapabilityRisk.HIGH
    assert ENGAGEMENT_MESSAGE_SEND_SPEC.approval_policy == ApprovalPolicy.ALWAYS
    assert ENGAGEMENT_MESSAGE_SEND_SPEC.idempotency_semantics == "idempotency_key"


@pytest.mark.asyncio
async def test_engagement_message_send_requires_approval_by_default(gateway_setup):
    gateway, repo, mock_client = gateway_setup

    req = GatewayExecutionRequest(
        run_id="run_send_1",
        capability_id="engagement.message.send",
        input_payload={
            "thread_id": "thread_123",
            "body": "Xin chào, đây là tin nhắn hỗ trợ.",
            "idempotency_key": "idem_send_1",
        },
        tool_call_id="call_send_1",
        checkpoint_ref="ckpt_send_1",
    )

    result = await gateway.execute(req)

    # 1. Gateway suspends execution with wait kind APPROVAL
    assert result.status == "waiting_approval"
    assert result.wait_descriptor is not None
    assert result.wait_descriptor.kind == WaitKind.APPROVAL
    assert result.output_payload is None

    # 2. Company Service Client must NOT be called before approval
    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_engagement_message_send_executes_after_approval(gateway_setup):
    gateway, repo, mock_client = gateway_setup

    mock_client.post.return_value = {
        "id": "msg_999",
        "messageId": "msg_999",
        "deliveryState": "queued",
    }

    req = GatewayExecutionRequest(
        run_id="run_send_2",
        capability_id="engagement.message.send",
        input_payload={
            "thread_id": "thread_456",
            "body": "Đã được phê duyệt phản hồi.",
            "idempotency_key": "idem_send_2",
        },
        tool_call_id="call_send_2",
        checkpoint_ref="ckpt_send_2",
    )

    # 1. First execution requires approval
    res1 = await gateway.execute(req)
    assert res1.status == "waiting_approval"
    appr_id = res1.wait_descriptor.related_ref

    # 2. Approve via repository
    await repo.decide_approval(appr_id, reviewer="approver_user", approved=True)

    # 3. Second execution with approval decision proceeds
    res2 = await gateway.execute(req)
    assert res2.status == "completed"
    assert res2.output_payload["message_id"] == "msg_999"
    assert res2.output_payload["delivery_state"] == "queued"

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/commercial/engagement/threads/thread_456/messages" in call_args[0][0]
    assert call_args[1]["json"]["body"] == "Đã được phê duyệt phản hồi."
    assert call_args[1]["json"]["idempotencyKey"] == "idem_send_2"


@pytest.mark.asyncio
async def test_engagement_message_send_handles_takeover_drop_or_conflict(gateway_setup):
    gateway, repo, mock_client = gateway_setup

    mock_client.post.side_effect = CompanyServiceError("Conflict: thread taken over", status_code=409)

    req = GatewayExecutionRequest(
        run_id="run_send_3",
        capability_id="engagement.message.send",
        input_payload={
            "thread_id": "thread_789",
            "body": "Tin nhắn thử",
            "idempotency_key": "idem_send_3",
        },
        tool_call_id="call_send_3",
        checkpoint_ref="ckpt_send_3",
    )

    res1 = await gateway.execute(req)
    appr_id = res1.wait_descriptor.related_ref
    await repo.decide_approval(appr_id, reviewer="approver_user", approved=True)

    res2 = await gateway.execute(req)
    assert res2.status == "completed"
    assert res2.output_payload["delivery_state"] == "cancelled"
