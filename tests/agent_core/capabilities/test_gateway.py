from __future__ import annotations

import pytest

from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.wait import WaitKind
from agent_core.governance.contracts import CapabilityRisk
from agent_core.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
    GatewayExecutionResult,
)
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.runs.repository import InMemoryRunRepository


@pytest.fixture
def test_setup():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    # Spec 1: Read capability (LOW risk)
    read_spec = CapabilitySpec(
        id="finance.invoice.get",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["invoice_id"],
            "properties": {"invoice_id": {"type": "string"}},
        },
    )

    call_counts = {"get": 0, "payout": 0}

    def get_handler(payload, ctx):
        call_counts["get"] += 1
        return {"invoice_id": payload["invoice_id"], "amount": 500, "status": "unpaid"}

    # Spec 2: Write capability (HIGH risk)
    write_spec = CapabilitySpec(
        id="finance.payout.execute",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
        input_schema={
            "type": "object",
            "required": ["invoice_id", "amount"],
            "properties": {
                "invoice_id": {"type": "string"},
                "amount": {"type": "number"},
            },
        },
    )

    def payout_handler(payload, ctx):
        call_counts["payout"] += 1
        return {"payout_id": "po_999", "status": "executed", "amount": payload["amount"]}

    registry.register(read_spec, get_handler)
    registry.register(write_spec, payout_handler)

    gateway = CapabilityGateway(registry=registry, repository=repo)

    return gateway, registry, repo, call_counts


@pytest.mark.asyncio
async def test_gateway_validation_failure(test_setup):
    gateway, _, _, _ = test_setup

    req = GatewayExecutionRequest(
        run_id="run_val_1",
        capability_id="finance.invoice.get",
        input_payload={},  # Thiếu invoice_id
    )
    res = await gateway.execute(req)

    assert res.status == "failed"
    assert len(res.validation_errors) > 0
    assert "Missing required field: 'invoice_id'" in res.validation_errors[0]


@pytest.mark.asyncio
async def test_gateway_allow_execution_and_events(test_setup):
    gateway, _, repo, call_counts = test_setup

    req = GatewayExecutionRequest(
        run_id="run_allow_1",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_101"},
    )
    res = await gateway.execute(req)

    assert res.status == "completed"
    assert res.output_payload == {"invoice_id": "inv_101", "amount": 500, "status": "unpaid"}
    assert call_counts["get"] == 1

    # Verify tool_call record
    tc = await repo.get_tool_call(res.tool_call_id)
    assert tc is not None
    assert tc.status == "completed"

    # Verify events
    events = await repo.list_events("run_allow_1")
    event_types = [e.event_type for e in events]
    assert "tool.requested" in event_types
    assert "policy.evaluated" in event_types
    assert "tool.started" in event_types
    assert "tool.completed" in event_types


@pytest.mark.asyncio
async def test_gateway_approval_pause_and_subsequent_resume(test_setup):
    gateway, _, repo, call_counts = test_setup

    req = GatewayExecutionRequest(
        run_id="run_appr_1",
        capability_id="finance.payout.execute",
        input_payload={"invoice_id": "inv_888", "amount": 10000},
        tool_call_id="call_payout_1",
        checkpoint_ref="ckpt_payout_step",
    )

    # 1. Chạy lần đầu -> phát hiện HIGH risk -> WAITING_APPROVAL
    res1 = await gateway.execute(req)
    assert res1.status == "waiting_approval"
    assert res1.wait_descriptor is not None
    assert res1.wait_descriptor.kind == WaitKind.APPROVAL
    assert call_counts["payout"] == 0

    # 2. Reviewer duyệt approval
    appr_id = res1.wait_descriptor.related_ref
    await repo.decide_approval(appr_id, reviewer="founder_1", approved=True)

    # 3. Chạy lại cùng tool_call_id sau khi đã duyệt
    res2 = await gateway.execute(req)
    assert res2.status == "completed"
    assert res2.output_payload["payout_id"] == "po_999"
    assert call_counts["payout"] == 1


@pytest.mark.asyncio
async def test_same_tool_called_twice_has_distinct_stable_identities(test_setup):
    """Test case 'same tool twice' (tiền đề Phase 6 case G):
    Gọi cùng 1 tool 2 lần trong cùng Run phải có 2 tool_call_id phân biệt, không đè nhau.
    """
    gateway, _, repo, _ = test_setup

    req1 = GatewayExecutionRequest(
        run_id="run_twice_1",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_A"},
        tool_call_id="call_invoice_A",
    )
    req2 = GatewayExecutionRequest(
        run_id="run_twice_1",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_B"},
        tool_call_id="call_invoice_B",
    )

    res1 = await gateway.execute(req1)
    res2 = await gateway.execute(req2)

    assert res1.tool_call_id == "call_invoice_A"
    assert res2.tool_call_id == "call_invoice_B"
    assert res1.tool_call_id != res2.tool_call_id

    # Đảm bảo lưu thành 2 records riêng biệt
    tc1 = await repo.get_tool_call("call_invoice_A")
    tc2 = await repo.get_tool_call("call_invoice_B")
    assert tc1 is not None and tc2 is not None
    assert tc1.input_payload["invoice_id"] == "inv_A"
    assert tc2.input_payload["invoice_id"] == "inv_B"


@pytest.mark.asyncio
async def test_idempotency_cache_replay(test_setup):
    """Chạy lần 2 với cùng idempotency_key phải trả về cached result, không gọi lại handler."""
    gateway, _, _, call_counts = test_setup

    req1 = GatewayExecutionRequest(
        run_id="run_idem_1",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_cached"},
        idempotency_key="idem_inv_cached_100",
    )
    res1 = await gateway.execute(req1)
    assert res1.status == "completed"
    assert res1.cached_idempotency is False
    assert call_counts["get"] == 1

    # Gọi lần 2
    req2 = GatewayExecutionRequest(
        run_id="run_idem_1",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_cached"},
        idempotency_key="idem_inv_cached_100",
    )
    res2 = await gateway.execute(req2)
    assert res2.status == "completed"
    assert res2.cached_idempotency is True
    assert call_counts["get"] == 1  # Handler KHÔNG bị gọi thêm lần nữa!
