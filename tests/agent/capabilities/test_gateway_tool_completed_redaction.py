from __future__ import annotations

import json

import pytest
from agent.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk
from agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_tool_completed_event_does_not_leak_raw_output_pii() -> None:
    """`tool.completed` là audit event persist Postgres — output thô của handler
    (có thể chứa PII/secret) không được ghi nguyên văn vào payload (Task 9)."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    spec = CapabilitySpec(
        id="finance.customer.lookup",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["customer_id"],
            "properties": {"customer_id": {"type": "string"}},
        },
    )

    # Handler trả về output chứa PII/secret thật, mô phỏng dữ liệu business-confidential.
    def handler(payload, ctx):
        return {
            "customer_id": payload["customer_id"],
            "email": "customer@example.com",
            "auth_header": "Bearer secret-token-should-not-leak",
        }

    registry.register(spec, handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    req = GatewayExecutionRequest(
        run_id="run_pii_1",
        capability_id="finance.customer.lookup",
        input_payload={"customer_id": "cust_1"},
        workspace_id="ws_1",
        context={"workspace_id": "ws_1"},
    )

    res = await gateway.execute(req)
    assert res.status == "completed"

    # GatewayExecutionResult (kênh hợp lệ để hiển thị/xử lý output cho caller thật)
    # vẫn phải giữ nguyên output thô — chỉ audit event log mới bị redact.
    assert res.output_payload["email"] == "customer@example.com"

    events = await repo.list_events("run_pii_1")
    completed_events = [e for e in events if e.event_type == "tool.completed"]
    assert len(completed_events) == 1
    event = completed_events[0]

    dumped = json.dumps(event.model_dump(mode="json"))
    assert "customer@example.com" not in dumped
    assert "Bearer secret-token-should-not-leak" not in dumped
    assert "secret-token-should-not-leak" not in dumped

    # Vẫn phải giữ đủ thông tin để chứng minh có output & tool_call_id để replay/trace,
    # nhưng KHÔNG được giữ nội dung thô — chỉ hash.
    assert event.payload["tool_call_id"] == req.tool_call_id
    assert "output" not in event.payload
    output_hash = event.payload.get("output_hash")
    assert isinstance(output_hash, str) and len(output_hash) == 64
    assert event.payload.get("output_present") is True
