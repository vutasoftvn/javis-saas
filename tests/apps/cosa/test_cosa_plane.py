from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from agent_core.capabilities.gateway import GatewayExecutionRequest
from agent_core.governance.contracts import PolicyOutcome
from agent_core.runs.repository import InMemoryRunRepository
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
    plane = build_cosa_agent_plane(company_client=mock_company_client, repository=InMemoryRunRepository())

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
    plane = build_cosa_agent_plane(company_client=mock_company_client, repository=InMemoryRunRepository())

    run_id = "run_cosa_payout_1"
    tool_call_id = "call_payout_gate_1"
    checkpoint_ref = "ckpt_payout_1"

    req = GatewayExecutionRequest(
        run_id=run_id,
        capability_id="finance.payout.execute",
        input_payload={
            "workspace_id": 1,
            "amount": 25000,
            "vendor": "Acme Cloud Services",
            "currency": "USD",
            "idempotency_key": "idem_po_25000_1",
        },
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        idempotency_key="idem_po_25000_1",
    )

    # 1. Gọi execute lần đầu -> Policy HIGH/payout chặn lại ở WAITING_APPROVAL
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
        reason="Approved Q3 Acme Hosting Payout",
    )
    assert decided.status == "approved"

    # 3. Resume / Re-invoke qua gateway
    res2 = await plane.gateway.execute(req)
    assert res2.status == "completed"
    assert res2.output_payload["payout_id"] == "po_9988"
    assert res2.output_payload["status"] == "committed"

    mock_company_client.post.assert_called_once_with(
        "/finance-legal/payouts",
        json={
            "workspaceId": 1,
            "amount": 25000,
            "vendor": "Acme Cloud Services",
            "currency": "USD",
            "description": "",
            "idempotencyKey": "idem_po_25000_1",
        },
    )
