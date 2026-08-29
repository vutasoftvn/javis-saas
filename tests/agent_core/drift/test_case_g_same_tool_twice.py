from __future__ import annotations

import pytest

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import CapabilityRisk
from agent_core.capabilities.approval_service import DurableApprovalService
from agent_core.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
)
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_case_g_same_tool_twice_independence():
    """Case G: Same tool twice (Master Guide §41.1 Case G).
    
    Kịch bản:
    1. Gọi cùng 1 capability `send_email` 2 lần trong cùng một Run.
    2. Invariant:
       - 2 lần gọi BẮT BUỘC có `tool_call_id` hoàn toàn khác nhau.
       - Tạo ra 2 bản ghi approval độc lập.
       - Phê duyệt của call #1 KHÔNG ĐƯỢC lây lan hoặc tự động duyệt call #2.
    """
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()

    sent_emails = []

    spec = CapabilitySpec(
        id="communication.email.send",
        risk=CapabilityRisk.HIGH,  # Cần approval
        input_schema={
            "type": "object",
            "required": ["to", "body"],
            "properties": {"to": {"type": "string"}, "body": {"type": "string"}},
        },
    )

    def send_email_handler(payload, ctx):
        sent_emails.append(payload)
        return {"status": "sent", "to": payload["to"]}

    registry.register(spec, send_email_handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)
    approval_service = DurableApprovalService(repository=repo)

    run_id = "run_case_g_multi_call"

    # 1. Lần gọi 1
    req1 = GatewayExecutionRequest(
        run_id=run_id,
        capability_id="communication.email.send",
        input_payload={"to": "client_alpha@acme.com", "body": "Invoice #1"},
        tool_call_id="call_email_turn_1",
        checkpoint_ref="ckpt_turn_1",
        workspace_id="ws_1",
        principal="user_1",
    )
    res1 = await gateway.execute(req1)
    assert res1.status == "waiting_approval"
    appr1_id = res1.wait_descriptor.related_ref

    # 2. Lần gọi 2
    req2 = GatewayExecutionRequest(
        run_id=run_id,
        capability_id="communication.email.send",
        input_payload={"to": "client_beta@acme.com", "body": "Invoice #2"},
        tool_call_id="call_email_turn_2",
        checkpoint_ref="ckpt_turn_2",
        workspace_id="ws_1",
        principal="user_1",
    )
    res2 = await gateway.execute(req2)
    assert res2.status == "waiting_approval"
    appr2_id = res2.wait_descriptor.related_ref

    # Verify ID phân biệt
    assert req1.tool_call_id != req2.tool_call_id
    assert appr1_id != appr2_id

    # 3. Reviewer duyệt Call #1
    await approval_service.submit_decision(
        approval_id=appr1_id,
        reviewer="sales_director",
        approved=True,
        reason="Approved email 1",
    )

    # 4. Thực thi lại Call #1 -> Thành công
    res1_resumed = await gateway.execute(req1)
    assert res1_resumed.status == "completed"
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "client_alpha@acme.com"

    # 5. Thử thực thi Call #2 -> VẪN BỊ CHẶN (Pending approval)
    res2_check = await gateway.execute(req2)
    assert res2_check.status == "waiting_approval"
    assert len(sent_emails) == 1  # Chưa được gửi

    # 6. Reviewer duyệt Call #2 -> Thực thi thành công
    await approval_service.submit_decision(
        approval_id=appr2_id,
        reviewer="sales_director",
        approved=True,
        reason="Approved email 2",
    )
    res2_resumed = await gateway.execute(req2)
    assert res2_resumed.status == "completed"
    assert len(sent_emails) == 2
    assert sent_emails[1]["to"] == "client_beta@acme.com"
