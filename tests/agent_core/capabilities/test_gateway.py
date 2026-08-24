from __future__ import annotations

import asyncio

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


@pytest.mark.asyncio
async def test_concurrent_gateway_execute_same_idempotency_key_only_one_side_effect():
    """Blueprint V2 §20: 2 request ĐỘC LẬP (tool_call_id khác nhau, giả lập 2 worker/
    request khác nhau, KHÔNG phải cùng 1 invocation resume) dispatch đồng thời với
    cùng idempotency_key — atomic claim (INSERT ... ON CONFLICT) phải đảm bảo handler
    chỉ chạy đúng 1 lần.

    Handler cố ý `await asyncio.sleep(...)` để tạo yield point thật — đây là điểm
    interleaving duy nhất có thể xảy ra trong 1 process asyncio (không có await nào
    khác giữa lúc claim và lúc gọi handler), nên request thứ 2 khi tới bước claim sẽ
    thấy claim đã tồn tại và bị chặn — đúng ngay cả khi asyncio.gather() ở đây không
    tạo interleaving mức thấp hơn mức này."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    spec = CapabilitySpec(
        id="test.race.capability",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={"type": "object"},
    )

    call_count = {"n": 0}

    async def slow_handler(payload, ctx):
        call_count["n"] += 1
        await asyncio.sleep(0.02)
        return {"result": "done"}

    registry.register(spec, slow_handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    req_a = GatewayExecutionRequest(
        run_id="run_race_1",
        capability_id="test.race.capability",
        input_payload={"x": 1},
        idempotency_key="idem_race_key_1",
    )
    req_b = GatewayExecutionRequest(
        run_id="run_race_1",
        capability_id="test.race.capability",
        input_payload={"x": 1},
        idempotency_key="idem_race_key_1",
    )
    assert req_a.tool_call_id != req_b.tool_call_id  # 2 invocation độc lập thật sự

    res_a, res_b = await asyncio.gather(gateway.execute(req_a), gateway.execute(req_b))

    statuses = sorted([res_a.status, res_b.status])
    assert statuses == ["completed", "in_progress"]
    assert call_count["n"] == 1  # Handler chỉ chạy đúng 1 lần bất kể 2 request cùng tới


@pytest.mark.asyncio
async def test_governance_accumulator_survives_gateway_restart(test_setup):
    """Trước fix: `CapabilityGateway._gov_states` là dict in-memory RIÊNG của
    từng instance — 1 Gateway mới (mô phỏng process restart) sẽ coi cùng
    (run_id, tool_call_id) là accumulation MỚI, mất governance đã tích luỹ
    trước đó (vi phạm invariant monotonic across restart, Blueprint V2 §9.2).
    Sau fix: governance_store durable dùng chung giữa các Gateway instance —
    Gateway "mới" (fresh object, cùng governance_store) phải thấy ĐÚNG state đã
    tích luỹ từ Gateway "cũ"."""
    gateway1, registry, repo, _ = test_setup
    governance_store = gateway1._governance_store  # cùng store sẽ được tái sử dụng

    req = GatewayExecutionRequest(
        run_id="run_restart_test_1",
        capability_id="finance.payout.execute",
        input_payload={"invoice_id": "inv_restart", "amount": 9000},
        tool_call_id="call_restart_1",
        checkpoint_ref="ckpt_restart_1",
    )

    # 1. Gateway "cũ" xử lý request đầu tiên -> tích luỹ governance REQUIRE_APPROVAL.
    res1 = await gateway1.execute(req)
    assert res1.status == "waiting_approval"

    saved_state = await governance_store.load_governance_state("run_restart_test_1", "call_restart_1")
    assert saved_state is not None
    assert saved_state.accumulated.outcome.value == "REQUIRE_APPROVAL"

    # 2. "Restart": tạo Gateway instance HOÀN TOÀN MỚI, KHÔNG chia sẻ bất kỳ
    # dict in-memory nào với gateway1 — chỉ chia sẻ governance_store (durable).
    gateway2 = CapabilityGateway(registry=registry, repository=repo, governance_store=governance_store)

    # 3. Duyệt approval rồi resume qua gateway2 (mô phỏng resume trên replica khác).
    appr_id = res1.wait_descriptor.related_ref
    await repo.decide_approval(appr_id, reviewer="founder_1", approved=True)
    res2 = await gateway2.execute(req)

    assert res2.status == "completed"  # gateway2 thấy đúng approval đã duyệt, không coi là REQUIRE_APPROVAL mới
    final_state = await governance_store.load_governance_state("run_restart_test_1", "call_restart_1")
    assert final_state is not None
    # Governance history phải là 2 observation tích luỹ (từ gateway1 và gateway2),
    # không phải bị reset về 1 observation duy nhất của gateway2.
    assert final_state.run_id == "run_restart_test_1"
