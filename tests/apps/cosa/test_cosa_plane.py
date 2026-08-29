from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from agent_core.capabilities.gateway import GatewayExecutionRequest
from agent_core.governance.contracts import PolicyOutcome
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {
        "tasks": [
            {"id": 101, "title": "Review Q3 OKRs", "status": "in_progress"},
            {"id": 102, "title": "Deploy Payment Cluster", "status": "completed"},
        ],
        "total": 2,
    }
    client.post.return_value = {
        "payout_id": "po_9988",
        "status": "committed",
        "transaction_ref": "tx_ref_7788",
    }
    return client


@pytest.mark.asyncio
async def test_cosa_read_capability_operations_task_list(mock_company_client):
    """Kiểm thử read capability (operations.task.list) qua CosaAgentPlane gateway."""
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    req = GatewayExecutionRequest(
        run_id="run_cosa_read_1",
        capability_id="operations.task.list",
        input_payload={"workspace_id": 1, "status": "in_progress"},
        tool_call_id="call_read_tasks_1",
    )

    res = await plane.gateway.execute(req)

    assert res.status == "completed"
    assert res.output_payload["total"] == 2
    assert len(res.output_payload["tasks"]) == 2
    mock_company_client.get.assert_called_once_with(
        "/operations/tasks",
        params={"workspaceId": 1, "status": "in_progress"},
    )


@pytest.mark.asyncio
async def test_cosa_write_capability_finance_payout_with_approval_flow(mock_company_client):
    """Kiểm thử write capability (finance.payout.execute) có approval gate qua CosaAgentPlane."""
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    run_id = "run_cosa_send_1"
    tool_call_id = "call_send_gate_1"
    checkpoint_ref = "ckpt_send_1"

    req = GatewayExecutionRequest(
        run_id=run_id,
        capability_id="engagement.message.send",
        input_payload={
            "thread_id": "th_1",
            "body": "Hello customer",
            "idempotency_key": "idem_send_1",
        },
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        workspace_id="ws_cosa_1",
        idempotency_key="idem_send_1",
    )

    # 1. Gọi execute lần đầu -> Policy HIGH chặn lại ở WAITING_APPROVAL
    res1 = await plane.gateway.execute(req)
    assert res1.status == "waiting_approval"
    assert res1.wait_descriptor is not None
    approval_id = res1.wait_descriptor.related_ref

    # Verify event audit trong repository
    events = await plane.repository.list_events(run_id)
    event_types = [e.event_type for e in events]
    assert "tool.requested" in event_types
    assert "approval.required" in event_types

    # 2. Reviewer (Founder) thẩm định và submit phê duyệt
    decided = await plane.approval_service.submit_decision(
        approval_id=approval_id,
        reviewer="founder_alice",
        approved=True,
        reason="Approved customer message",
    )
    assert decided.status == "approved"

    # 3. Resume / Re-invoke qua gateway
    mock_company_client.post.return_value = {"messageId": "msg_9988", "deliveryState": "delivered"}
    res2 = await plane.gateway.execute(req)
    assert res2.status == "completed"
    assert res2.output_payload["message_id"] == "msg_9988"


@pytest.mark.asyncio
async def test_cosa_send_missing_workspace_assert_typed_failure(mock_company_client):
    """Context không rơi về 'default' — assert typed failure khi thiếu workspace."""
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    req = GatewayExecutionRequest(
        run_id="run_missing_ws_test",
        capability_id="engagement.message.send",
        input_payload={
            "thread_id": "th_1",
            "body": "Hello customer",
            "idempotency_key": "idem_send_no_ws",
        },
        tool_call_id="call_no_ws",
        # workspace_id omitted / None
    )

    res = await plane.gateway.execute(req)
    assert res.status == "failed"
    assert "tenancy unresolved" in res.error_message.lower()
    assert res.failure is not None


@pytest.mark.asyncio
async def test_cosa_approval_of_tool_call_a_does_not_open_tool_call_b(mock_company_client):
    """Approval của tool call A không mở tool call B (exact invocation ledger)."""
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    req_a = GatewayExecutionRequest(
        run_id="run_tool_calls_ab",
        capability_id="engagement.message.send",
        input_payload={"thread_id": "th_1", "body": "Msg A", "idempotency_key": "idem_a"},
        tool_call_id="call_A",
        checkpoint_ref="ckpt_A",
        workspace_id="ws_cosa_1",
    )
    req_b = GatewayExecutionRequest(
        run_id="run_tool_calls_ab",
        capability_id="engagement.message.send",
        input_payload={"thread_id": "th_1", "body": "Msg B", "idempotency_key": "idem_b"},
        tool_call_id="call_B",
        checkpoint_ref="ckpt_B",
        workspace_id="ws_cosa_1",
    )

    # 1. Cả 2 đều đợi approval
    res_a = await plane.gateway.execute(req_a)
    res_b = await plane.gateway.execute(req_b)
    assert res_a.status == "waiting_approval"
    assert res_b.status == "waiting_approval"

    # 2. Duyệt riêng approval của A
    appr_id_a = res_a.wait_descriptor.related_ref
    await plane.approval_service.submit_decision(
        approval_id=appr_id_a,
        reviewer="founder_alice",
        approved=True,
    )

    # 3. Resume A -> completed
    mock_company_client.post.return_value = {"messageId": "msg_A", "deliveryState": "delivered"}
    res_a_resume = await plane.gateway.execute(req_a)
    assert res_a_resume.status == "completed"

    # 4. Resume B -> VẪN waiting_approval, không bị mở ké
    res_b_resume = await plane.gateway.execute(req_b)
    assert res_b_resume.status == "waiting_approval"


@pytest.mark.asyncio
async def test_cosa_human_takeover_blocks_resume(mock_company_client):
    """Human takeover hoặc emergency lock chặn resume."""
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )

    req = GatewayExecutionRequest(
        run_id="run_takeover_1",
        capability_id="engagement.message.send",
        input_payload={"thread_id": "th_1", "body": "Takeover test", "idempotency_key": "idem_to_1"},
        tool_call_id="call_takeover_1",
        checkpoint_ref="ckpt_to_1",
        workspace_id="ws_cosa_1",
    )

    res1 = await plane.gateway.execute(req)
    assert res1.status == "waiting_approval"

    appr_id = res1.wait_descriptor.related_ref
    await plane.approval_service.submit_decision(
        approval_id=appr_id,
        reviewer="founder_alice",
        approved=True,
    )

    # Khi có human takeover trên thread/context
    req.context = {"human_takeover": True}
    res2 = await plane.gateway.execute(req)
    assert res2.status == "denied"
    assert "human takeover" in res2.error_message.lower()

