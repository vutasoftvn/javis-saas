from __future__ import annotations

import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from agent.runs.stream_events import InMemoryRunStreamEventRepository
from apps.cosa.api.app import create_cosa_app
from apps.cosa.api.event_stream import CosaEventStreamManager
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


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


def _client_for_identity(correlation_db, *, workspace_id: str, role_id: str = "founder"):
    app = create_cosa_app()
    app.state.plane = type("DummyPlane", (), {
        "correlation_db": correlation_db,
    })()
    override_authenticated_identity(app, workspace_id=workspace_id, role_id=role_id)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def client_a(correlation_db):
    return _client_for_identity(correlation_db, workspace_id="ws_ops_a")


@pytest.fixture
def client_b(correlation_db):
    return _client_for_identity(correlation_db, workspace_id="ws_ops_b")


@pytest.fixture
def operator_client(correlation_db):
    return _client_for_identity(correlation_db, workspace_id="ws_ops_a")


@pytest.fixture
def member_client(correlation_db):
    return _client_for_identity(correlation_db, workspace_id="ws_ops_a", role_id="member")


@pytest.fixture
def unsecured_client(correlation_db):
    app = create_cosa_app()
    app.state.plane = type("DummyPlane", (), {
        "correlation_db": correlation_db,
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
async def test_correlation_chain_links_event_to_run_without_tool_result(client_a, seeded_chain):
    r = await client_a.get(f"/agent/events/correlation/{seeded_chain.correlation_id}")
    assert r.status_code == 200
    data = r.json()
    kinds = [step["kind"] for step in data["chain"]]
    assert kinds == ["event", "inbox", "scheduled_task", "run", "artifact"]
    dump = r.text.lower()
    assert "tool_result" not in dump and "access_token" not in dump


@pytest.mark.asyncio
async def test_missing_identity_cannot_read_correlation(unsecured_client, seeded_chain):
    assert (
        await unsecured_client.get(f"/agent/events/correlation/{seeded_chain.correlation_id}")
    ).status_code == 401


@pytest.mark.asyncio
async def test_workspace_b_gets_not_found_for_workspace_a_chain(client_b, seeded_chain_a):
    response = await client_b.get(f"/agent/events/correlation/{seeded_chain_a.correlation_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_member_cannot_retry_and_missing_event_is_not_success(member_client, operator_client):
    assert (await member_client.post("/agent/events/missing/retry")).status_code == 403
    assert (await operator_client.post("/agent/events/missing/retry")).status_code == 404


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
