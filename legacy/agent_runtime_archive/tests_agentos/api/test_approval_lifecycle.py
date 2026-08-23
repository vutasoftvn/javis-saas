from __future__ import annotations

import time
import jwt
import pytest
from fastapi.testclient import TestClient

from agentos.api.app import app
from agentos.api.auth import JWT_SECRET
from agentos.api.chat.routes import get_event_stream_manager, set_agent_runtime
from agentos.api.db.session import reset_db_for_testing
from agentos.core.approval import ApprovalService
from agentos.core.model_provider import ModelProvider, ModelResponse, ToolCallRequest
from agentos.core.policy import ToolPermission, ToolRiskLevel
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry
from agentos.tools.spec import ToolSpecV2


def _make_token(user_id="u1", workspace_id="ws1", company_id="comp1", role="founder"):
    return jwt.encode(
        {"sub": user_id, "workspace_id": workspace_id, "company_id": company_id, "role": role},
        JWT_SECRET,
        algorithm="HS256",
    )


class _RetryingToolModel(ModelProvider):
    def __init__(self):
        self.call_count = 0

    async def generate(self, system_prompt, messages):
        self.call_count += 1
        if self.call_count <= 2:
            return ModelResponse(
                text=None,
                tool_call=ToolCallRequest(tool_name="finance.transfer.funds", arguments={"amount": 5000}),
            )
        return ModelResponse(text="Transfer completed successfully.", tool_call=None)


def _wait_for_event(stream_mgr, run_id, event_type, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        events = stream_mgr.get_events(run_id)
        match = next((e for e in events if e.event_type == event_type), None)
        if match is not None:
            return match, events
        time.sleep(0.02)
    return None, stream_mgr.get_events(run_id)


def test_approval_lifecycle_approved_maintains_single_run_and_correlation_id():
    reset_db_for_testing("sqlite:///:memory:")

    invoked_args = []

    async def transfer_handler(args):
        invoked_args.append(args)
        return {"status": "transferred", "amount": args.get("amount")}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="finance.transfer.funds",
            description="Transfer funds",
            handler=transfer_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )
    approval_svc = ApprovalService()
    runtime = AgentRuntime(_RetryingToolModel(), registry, approval_service=approval_svc)
    set_agent_runtime(runtime)

    client = TestClient(app)
    custom_correlation = "corr-test-12345"
    headers = {
        "Authorization": f"Bearer {_make_token()}",
        "x-correlation-id": custom_correlation,
    }

    # 1. Create conversation
    res = client.post("/agent/conversations", json={"title": "Transfer Request"}, headers=headers)
    assert res.status_code == 201
    conv_id = res.json()["id"]

    # 2. Post message requiring approval
    res = client.post(
        f"/agent/conversations/{conv_id}/messages",
        json={"content": "Transfer 5000 to vendor"},
        headers=headers,
    )
    assert res.status_code == 202
    api_run_id = res.json()["run_id"]
    stream_mgr = get_event_stream_manager()

    # 3. Verify approval.required event
    approval_event, events_before = _wait_for_event(stream_mgr, api_run_id, "approval.required")
    assert approval_event is not None
    assert approval_event.payload["tool_name"] == "finance.transfer.funds"
    approval_id = approval_event.payload["approval_id"]

    # 4. Approve the request
    res = client.post(
        f"/agent/approvals/{approval_id}/decision",
        json={"approved": True, "reason": "Authorized by CFO"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "APPROVED"

    # 5. Wait for run.completed on the EXACT SAME run_id
    completed_event, events_after = _wait_for_event(stream_mgr, api_run_id, "run.completed")
    assert completed_event is not None
    assert len(invoked_args) == 1
    assert invoked_args[0]["amount"] == 5000

    # 6. Verify single run_id in event stream manager (no second disconnected run created)
    assert len(stream_mgr._run_events) == 1
    assert api_run_id in stream_mgr._run_events

    # 7. Verify correlation_id is identical across all events
    for event in events_after:
        assert event.correlation_id == custom_correlation, f"Event {event.event_type} lost correlation_id"


def test_approval_decision_duplicate_call_is_rejected():
    reset_db_for_testing("sqlite:///:memory:")

    async def transfer_handler(args):
        return {"status": "ok"}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="finance.transfer.funds",
            description="Transfer funds",
            handler=transfer_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )
    approval_svc = ApprovalService()
    runtime = AgentRuntime(_RetryingToolModel(), registry, approval_service=approval_svc)
    set_agent_runtime(runtime)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_make_token()}"}

    res = client.post("/agent/conversations", json={"title": "Dup Decision Test"}, headers=headers)
    conv_id = res.json()["id"]

    res = client.post(
        f"/agent/conversations/{conv_id}/messages",
        json={"content": "Transfer 5000"},
        headers=headers,
    )
    api_run_id = res.json()["run_id"]
    stream_mgr = get_event_stream_manager()

    approval_event, _ = _wait_for_event(stream_mgr, api_run_id, "approval.required")
    approval_id = approval_event.payload["approval_id"]

    # First decision -> Success
    res1 = client.post(
        f"/agent/approvals/{approval_id}/decision",
        json={"approved": True, "reason": "First decision"},
        headers=headers,
    )
    assert res1.status_code == 200

    # Second decision -> 400 Bad Request (prevent double-decision / double-execution)
    res2 = client.post(
        f"/agent/approvals/{approval_id}/decision",
        json={"approved": True, "reason": "Second decision"},
        headers=headers,
    )
    assert res2.status_code == 400
    assert "already decided" in res2.json()["detail"].lower()


def test_approval_decision_rejects_nonexistent_approval_id():
    # roadmap 12a.6: xác nhận không thể "brute-force" hoặc giả mạo approval_id
    # để thực thi 1 quyết định approval chưa từng được tạo.
    reset_db_for_testing("sqlite:///:memory:")

    approval_svc = ApprovalService()
    runtime = AgentRuntime(_RetryingToolModel(), ToolRegistry(), approval_service=approval_svc)
    set_agent_runtime(runtime)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_make_token()}"}

    res = client.post(
        "/agent/approvals/forged-nonexistent-approval-id/decision",
        json={"approved": True, "reason": "attempted forgery"},
        headers=headers,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_approval_decision_rejected_handles_gracefully():
    reset_db_for_testing("sqlite:///:memory:")

    async def transfer_handler(args):
        return {"status": "ok"}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="finance.transfer.funds",
            description="Transfer funds",
            handler=transfer_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )
    approval_svc = ApprovalService()
    runtime = AgentRuntime(_RetryingToolModel(), registry, approval_service=approval_svc)
    set_agent_runtime(runtime)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {_make_token()}"}

    res = client.post("/agent/conversations", json={"title": "Reject Decision Test"}, headers=headers)
    conv_id = res.json()["id"]

    res = client.post(
        f"/agent/conversations/{conv_id}/messages",
        json={"content": "Transfer 5000"},
        headers=headers,
    )
    api_run_id = res.json()["run_id"]
    stream_mgr = get_event_stream_manager()

    approval_event, _ = _wait_for_event(stream_mgr, api_run_id, "approval.required")
    approval_id = approval_event.payload["approval_id"]

    # Reject decision
    res = client.post(
        f"/agent/approvals/{approval_id}/decision",
        json={"approved": False, "reason": "Budget limit exceeded"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "DENIED"

    # Wait for run.failed event
    failed_event, _ = _wait_for_event(stream_mgr, api_run_id, "run.failed")
    assert failed_event is not None
    assert "rejected" in failed_event.payload["error"].lower() or "denied" in failed_event.payload["error"].lower()
