import time

import pytest
import jwt
from fastapi.testclient import TestClient

from agentos.api.app import app
from agentos.api.auth import JWT_SECRET
from agentos.api.chat.routes import set_agent_runtime
from agentos.api.db.session import reset_db_for_testing
from agentos.core.models import AgentResult, AgentRunStatus
from agentos.core.runtime import AgentRuntime


class StubContext:
    def __init__(self, knowledge_snippets=None):
        self.knowledge_snippets = knowledge_snippets or []


class StubRuntime:
    def __init__(self, knowledge_snippets=None, emit_tool_calls=False):
        self.last_task = None
        self._approval_service = None
        self.last_context = StubContext(knowledge_snippets=knowledge_snippets)
        self._emit_tool_calls = emit_tool_calls

    async def run(self, task, on_tool_event=None):
        self.last_task = task
        if self._emit_tool_calls and on_tool_event is not None:
            on_tool_event("tool.requested", {"tool_name": "operations.task.list", "arguments": {}})
            on_tool_event("tool.started", {"tool_name": "operations.task.list", "arguments": {}})
            on_tool_event("tool.completed", {"tool_name": "operations.task.list", "result": {"items": []}})
        return AgentResult(
            run_id=task.metadata.get("run_id", "stub-run"),
            status=AgentRunStatus.COMPLETED,
            output=f"Echo answer for: {task.goal}",
            tool_calls_made=1,
        )


def make_token(user_id="user-1", workspace_id="ws-1", company_id="comp-1", role="founder"):
    return jwt.encode(
        {
            "sub": user_id,
            "workspace_id": workspace_id,
            "company_id": company_id,
            "role": role,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def setup_test_db():
    reset_db_for_testing("sqlite:///:memory:")
    stub_rt = StubRuntime()
    from agentos.core.approval import ApprovalService
    stub_rt._approval_service = ApprovalService()
    set_agent_runtime(stub_rt)
    yield


def test_unauthenticated_request_fails():
    client = TestClient(app)
    res = client.get("/agent/conversations")
    assert res.status_code == 401
    assert "Missing Authorization header" in res.text


def test_invalid_token_fails():
    client = TestClient(app)
    res = client.get("/agent/conversations", headers={"Authorization": "Bearer invalid_garbage"})
    assert res.status_code == 401


def test_create_and_list_conversations():
    client = TestClient(app)
    token = make_token(user_id="u1", workspace_id="ws1", company_id="comp1", role="founder")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create conversation
    res = client.post(
        "/agent/conversations",
        json={"title": "Q3 Marketing Strategy", "active_agent_profile": "marketing_lead"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Q3 Marketing Strategy"
    assert data["company_id"] == "comp1"
    assert data["workspace_id"] == "ws1"
    assert data["active_agent_profile"] == "marketing_lead"
    conv_id = data["id"]

    # 2. List conversations
    res = client.get("/agent/conversations", headers=headers)
    assert res.status_code == 200
    list_data = res.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == conv_id

    # 3. Get single conversation
    res = client.get(f"/agent/conversations/{conv_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == conv_id


def test_cross_tenant_isolation_returns_404_without_leaking():
    client = TestClient(app)
    token1 = make_token(user_id="u1", workspace_id="ws1", company_id="comp1", role="founder")
    token2 = make_token(user_id="u2", workspace_id="ws2", company_id="comp2", role="user")

    # Tenant 1 creates a conversation
    res = client.post(
        "/agent/conversations",
        json={"title": "Confidential Deal"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    conv_id = res.json()["id"]

    # Tenant 2 tries to access Tenant 1's conversation
    res = client.get(
        f"/agent/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 404

    # Tenant 2 lists conversations -> sees 0
    res = client.get("/agent/conversations", headers={"Authorization": f"Bearer {token2}"})
    assert res.json()["total"] == 0


def test_patch_and_soft_delete_conversation():
    client = TestClient(app)
    token = make_token(user_id="u1", workspace_id="ws1", company_id="comp1")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/agent/conversations", json={"title": "Old Title"}, headers=headers)
    conv_id = res.json()["id"]

    # Update title
    res = client.patch(
        f"/agent/conversations/{conv_id}",
        json={"title": "Updated Title"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"

    # Soft delete (archive)
    res = client.patch(
        f"/agent/conversations/{conv_id}",
        json={"archived": True},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["archived_at"] is not None

    # List default excludes archived
    res = client.get("/agent/conversations", headers=headers)
    assert res.json()["total"] == 0

    # List with include_archived=true includes it
    res = client.get("/agent/conversations?include_archived=true", headers=headers)
    assert res.json()["total"] == 1


def test_post_message_and_trigger_run():
    client = TestClient(app)
    token = make_token(user_id="u1", workspace_id="ws1", company_id="comp1", role="founder")
    headers = {"Authorization": f"Bearer {token}"}

    # Create conversation
    res = client.post("/agent/conversations", json={"title": "Run Test"}, headers=headers)
    conv_id = res.json()["id"]

    # Post message with attachment
    res = client.post(
        f"/agent/conversations/{conv_id}/messages",
        json={
            "content": "Please analyze our balance sheet",
            "attachments": [
                {
                    "file_name": "balance.pdf",
                    "media_type": "application/pdf",
                    "object_ref": "s3://bucket/balance.pdf",
                    "size": 1024,
                }
            ],
        },
        headers=headers,
    )
    assert res.status_code == 202
    data = res.json()
    assert "run_id" in data
    assert data["conversation_id"] == conv_id
    assert data["status"] == "RUNNING"


def test_cancel_run_and_approval_decision():
    client = TestClient(app)
    token = make_token(user_id="u1", workspace_id="ws1", company_id="comp1")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Cancel run
    res = client.post("/agent/runs/run-xyz/cancel", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"

    # 2. Decision on approval
    stub_rt = StubRuntime()
    from agentos.core.approval import ApprovalService
    stub_rt._approval_service = ApprovalService()
    appr = stub_rt._approval_service.request_approval(
        action="transfer_funds",
        subject="1000 USD",
        requester="finance_agent",
        run_id="run-123",
    )
    set_agent_runtime(stub_rt)

    res = client.post(
        f"/agent/approvals/{appr.id}/decision",
        json={"approved": True, "reason": "Approved by founder"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["reviewer"] == "user:u1"


def test_tool_events_citation_and_attachment_processed_are_streamed():
    """Phase 4a: SSE stream must surface tool.requested/started/completed,
    citation, and attachment.processed — not just run/message lifecycle events."""
    from agentos.api.chat.routes import get_event_stream_manager

    client = TestClient(app)
    token = make_token(user_id="u1", workspace_id="ws1", company_id="comp1", role="founder")
    headers = {"Authorization": f"Bearer {token}"}

    stub_rt = StubRuntime(
        knowledge_snippets=["The company's Q3 revenue was $1.2M."],
        emit_tool_calls=True,
    )
    from agentos.core.approval import ApprovalService

    stub_rt._approval_service = ApprovalService()
    set_agent_runtime(stub_rt)

    res = client.post("/agent/conversations", json={"title": "Tool Event Test"}, headers=headers)
    conv_id = res.json()["id"]

    res = client.post(
        f"/agent/conversations/{conv_id}/messages",
        json={
            "content": "List open tasks",
            "attachments": [
                {
                    "file_name": "report.pdf",
                    "media_type": "application/pdf",
                    "object_ref": "s3://bucket/report.pdf",
                    "size": 2048,
                }
            ],
        },
        headers=headers,
    )
    assert res.status_code == 202
    run_id = res.json()["run_id"]

    stream_mgr = get_event_stream_manager()

    # attachment.processed is emitted synchronously before the response
    # returns, so it must already be present.
    events = stream_mgr.get_events(run_id)
    event_types = [e.event_type for e in events]
    assert "attachment.processed" in event_types

    # tool.* events are emitted by the background task (asyncio.create_task);
    # poll briefly for it to finish rather than assuming it's instant.
    deadline = time.time() + 2.0
    while time.time() < deadline:
        events = stream_mgr.get_events(run_id)
        event_types = [e.event_type for e in events]
        if "run.completed" in event_types:
            break
        time.sleep(0.02)

    assert "tool.requested" in event_types
    assert "tool.started" in event_types
    assert "tool.completed" in event_types
    assert "citation" in event_types
    assert "run.completed" in event_types

    tool_started = next(e for e in events if e.event_type == "tool.started")
    assert tool_started.payload["tool_name"] == "operations.task.list"

    citation = next(e for e in events if e.event_type == "citation")
    assert citation.payload["text"] == "The company's Q3 revenue was $1.2M."

    attachment_event = next(e for e in events if e.event_type == "attachment.processed")
    assert attachment_event.payload["file_name"] == "report.pdf"

    # Sequence must stay monotonic across the whole run, tool events included.
    sequences = [e.sequence for e in events]
    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))
