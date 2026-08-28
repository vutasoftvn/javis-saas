from __future__ import annotations

import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from apps.cosa.api.app import create_cosa_app
from apps.cosa.api.event_stream import CosaEventStreamManager


class StubCorrelationDb:
    def __init__(self):
        self.inbox_records = {}
        self.tasks = {}
        self.runs = {}
        self.artifacts = {}

    def seed_chain(self, workspace_id: str, correlation_id: str):
        event_id = str(uuid.uuid4())
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        artifact_id = f"art_{uuid.uuid4().hex[:8]}"

        self.inbox_records[correlation_id] = {
            "workspace_id": workspace_id,
            "event_id": event_id,
            "event_type": "operations.task.created.v1",
            "correlation_id": correlation_id,
            "scheduled_task_id": task_id,
            "received_at": "2026-08-28T10:00:00Z",
        }
        self.tasks[task_id] = {
            "task_id": task_id,
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "run_id": run_id,
            "created_at": "2026-08-28T10:00:01Z",
        }
        self.runs[run_id] = {
            "run_id": run_id,
            "workspace_id": workspace_id,
            "task_id": task_id,
            "correlation_id": correlation_id,
            "started_at": "2026-08-28T10:00:02Z",
        }
        self.artifacts[artifact_id] = {
            "artifact_id": artifact_id,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "created_at": "2026-08-28T10:00:05Z",
        }
        return type("Chain", (), {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "event_id": event_id,
            "task_id": task_id,
            "run_id": run_id,
            "artifact_id": artifact_id,
        })()


@pytest.fixture
def correlation_db():
    return StubCorrelationDb()


@pytest.fixture
def ops_client(correlation_db):
    app = create_cosa_app()
    app.state.plane = type("DummyPlane", (), {
        "correlation_db": correlation_db,
        "caller_workspace_id": "ws_ops_a",
    })()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def ops_client_b(correlation_db):
    app = create_cosa_app()
    app.state.plane = type("DummyPlane", (), {
        "correlation_db": correlation_db,
        "caller_workspace_id": "ws_ops_b",
    })()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def seeded_chain(correlation_db):
    return correlation_db.seed_chain("ws_ops_a", "corr_chain_1")


@pytest.fixture
def seeded_chain_a(correlation_db):
    return correlation_db.seed_chain("ws_ops_a", "corr_chain_2")


@pytest.mark.asyncio
async def test_correlation_chain_links_event_to_run_without_tool_result(ops_client, seeded_chain):
    r = await ops_client.get(
        f"/agent/events/correlation/{seeded_chain.correlation_id}",
        params={"workspaceId": seeded_chain.workspace_id},
    )
    assert r.status_code == 200
    data = r.json()
    kinds = [step["kind"] for step in data["chain"]]
    assert kinds == ["event", "inbox", "scheduled_task", "run", "artifact"]
    dump = r.text.lower()
    assert "tool_result" not in dump and "access_token" not in dump


@pytest.mark.asyncio
async def test_workspace_b_cannot_read_workspace_a_correlation(ops_client_b, seeded_chain_a):
    r = await ops_client_b.get(
        f"/agent/events/correlation/{seeded_chain_a.correlation_id}",
        params={"workspaceId": seeded_chain_a.workspace_id},
    )
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_sse_persistence_redacts_non_allowlisted_payload_at_storage_time():
    fake_repo = InMemoryRunStreamEventRepository()
    stream_manager = CosaEventStreamManager()

    await stream_manager.emit(
        fake_repo,
        run_id="r1",
        conversation_id="conv_1",
        event_type="tool.raw_output",
        payload={"secret": "x", "blob": "y"},
    )
    stored = (await fake_repo.list_since("r1"))[-1]
    assert "secret" not in json.dumps(stored.payload)
    assert set(stored.payload.keys()) <= {"event_ref", "hash", "classification"}
