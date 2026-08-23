"""Phase 6b / §5.3 regression guard: approval resume must continue the SAME
run the client is subscribed to via SSE, not a new internal run_id.

This directly exercises AgentRuntime.run() (not a stub), because the bug this
guards against is specifically that AgentRuntime always minted a fresh random
AgentRun.id regardless of the caller-supplied run_id in task.metadata — which
silently broke agentos/api/chat/routes.py's `_pending_runs` lookup (keyed by
the API-level run_id) against ApprovalService.find_by_run_and_action() (keyed
by the Executor's internal trace.run_id). With a stub AgentRuntime this bug is
invisible, since stubs don't reproduce AgentRuntime's own run_id generation.
"""
import time

import jwt

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
    """Requests the same HIGH-risk tool on both the initial attempt and the
    post-approval resume — the realistic case where the model retries the
    action now that it's approved, which is what find_by_run_and_action()
    must actually short-circuit (a model that never retries the tool would
    trivially "pass" without exercising that dedup path at all)."""

    def __init__(self):
        self.call_count = 0

    async def generate(self, system_prompt, messages):
        self.call_count += 1
        if self.call_count <= 2:
            return ModelResponse(
                text=None,
                tool_call=ToolCallRequest(tool_name="ops.deploy.prod", arguments={}),
            )
        return ModelResponse(text="Deploy completed.", tool_call=None)


def _wait_for_event(stream_mgr, run_id, event_type, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        events = stream_mgr.get_events(run_id)
        match = next((e for e in events if e.event_type == event_type), None)
        if match is not None:
            return match, events
        time.sleep(0.02)
    return None, stream_mgr.get_events(run_id)


def test_approval_resume_continues_same_client_visible_run():
    reset_db_for_testing("sqlite:///:memory:")

    async def deploy_handler(args):
        return {"status": "deployed"}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="ops.deploy.prod",
            description="Deploy to production",
            handler=deploy_handler,
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

    res = client.post("/agent/conversations", json={"title": "Resume Test"}, headers=headers)
    conv_id = res.json()["id"]

    res = client.post(
        f"/agent/conversations/{conv_id}/messages",
        json={"content": "Deploy to prod"},
        headers=headers,
    )
    api_run_id = res.json()["run_id"]
    stream_mgr = get_event_stream_manager()

    approval_event, _ = _wait_for_event(stream_mgr, api_run_id, "approval.required")
    assert approval_event is not None, "approval.required never reached the client-visible run"
    approval_id = approval_event.payload["approval_id"]

    res = client.post(
        f"/agent/approvals/{approval_id}/decision",
        json={"approved": True, "reason": "test"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "APPROVED"

    completed_event, events = _wait_for_event(stream_mgr, api_run_id, "run.completed")
    event_types = [e.event_type for e in events]
    assert completed_event is not None, (
        f"run.completed never arrived on the original run_id={api_run_id} after approval "
        f"(events seen: {event_types}) — resume created a disconnected run instead of "
        "continuing the one the client is subscribed to."
    )

    # The retried tool call must proceed straight through (no second
    # approval.required) once find_by_run_and_action() finds it APPROVED.
    assert event_types.count("approval.required") == 1
    assert "tool.started" in event_types
    assert "tool.completed" in event_types

    # Exactly one AgentRun's worth of activity happened — never a second,
    # disconnected run_id that the client never hears about.
    assert len(get_event_stream_manager()._run_events) == 1
