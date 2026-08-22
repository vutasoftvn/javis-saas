"""End-to-end pilot: agentos ToolRegistry -> real EncoreClient -> live
services/{operations,commercial} HTTP API -> Postgres -> task.created /
task.completed domain events.

This is the Giai đoạn 2 pilot from docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md
(operations.tasks) extended to services/commercial (sales leads) — the
first proof that `services/` (previously "0 consumer" per
docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md) can serve a real write
from the agentos/ side over actual HTTP, not a mocked EncoreClient. Unlike
operations.tasks, services/commercial has no idempotency_key column yet and
no domain event defined for lead creation (per ADR-012, migrations for it
are staged but not wired) — this pilot deliberately does not add either,
since inventing event/idempotency semantics for a domain nobody asked to
extend would be scope creep, not gap-closing.

Requires a live Encore dev server for `services/` (`encore run` from the
`services/` directory, default http://127.0.0.1:4000). Skipped automatically
when that server isn't reachable, so it does not fail CI environments that
don't run the Encore dev stack — the mocked unit tests in
test_encore_tool_bindings.py remain the fast, always-on coverage for tool
wiring; this file is the live-infra complement, not a replacement.

Event verification (`task.created` on create, `task.completed` on status
-> done) is NOT re-derived here via cross-language pubsub inspection from
Python -- that would be fragile. It is instead verified directly, with
`vi.spyOn`, in services/operations/task.test.ts (same Giai đoạn 2 change).
This file proves the HTTP path that triggers those publishes actually works
end-to-end; the TS test proves the publish itself happens exactly once per
genuine state transition.
"""
from __future__ import annotations

import httpx
import pytest

from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry

ENCORE_URL = "http://127.0.0.1:4000"


def _encore_service_reachable() -> bool:
    try:
        # Any 2xx/4xx response means the HTTP server is up; only a
        # connection failure means "not running".
        httpx.get(f"{ENCORE_URL}/operations/tasks", params={"workspaceId": 1}, timeout=1.0)
        return True
    except httpx.RequestError:
        return False


pytestmark = pytest.mark.skipif(
    not _encore_service_reachable(),
    reason="services/ Encore dev server not reachable at http://127.0.0.1:4000 (run `encore run` from services/)",
)


@pytest.fixture
def encore_client() -> EncoreClient:
    return EncoreClient(base_url=ENCORE_URL)


@pytest.fixture
def registry(encore_client: EncoreClient) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register_cluster_tools(encore_client=encore_client)
    return reg


async def _make_workspace(encore_client: EncoreClient, name: str) -> int:
    # Workspace creation isn't exposed as an agent tool (identity_tools.py
    # only has workspace_get/workforce_member_list) — this is real HTTP
    # test setup against the live identity cluster, same server, same DB.
    result = await encore_client.post("/identity/workspaces", json={"name": name})
    return result["id"]


@pytest.mark.asyncio
async def test_agent_tool_creates_a_real_task_over_http(encore_client: EncoreClient, registry: ToolRegistry):
    workspace_id = await _make_workspace(encore_client, "Pilot E2E Workspace")

    created = await registry.invoke(
        "task_create", {"workspaceId": workspace_id, "title": "Pilot task from agentos"}
    )

    assert created["id"] > 0
    assert created["workspaceId"] == workspace_id
    assert created["status"] == "todo"

    listed = await registry.invoke("task_list", {"workspaceId": workspace_id})
    assert any(t["id"] == created["id"] for t in listed["tasks"])


@pytest.mark.asyncio
async def test_agent_tool_transitions_a_real_task_to_done_over_http(
    encore_client: EncoreClient, registry: ToolRegistry
):
    workspace_id = await _make_workspace(encore_client, "Pilot E2E Status Workspace")
    created = await registry.invoke(
        "task_create", {"workspaceId": workspace_id, "title": "Ship the pilot"}
    )

    done = await registry.invoke("task_update_status", {"id": created["id"], "status": "done"})

    assert done["status"] == "done"
    assert done["id"] == created["id"]


@pytest.mark.asyncio
async def test_agent_tool_retry_with_idempotency_key_returns_the_same_task(
    encore_client: EncoreClient, registry: ToolRegistry
):
    workspace_id = await _make_workspace(encore_client, "Pilot E2E Idempotency Workspace")

    first = await registry.invoke(
        "task_create",
        {"workspaceId": workspace_id, "title": "Send report", "idempotencyKey": "pilot-e2e-key-1"},
    )
    retried = await registry.invoke(
        "task_create",
        {"workspaceId": workspace_id, "title": "Send report (retry)", "idempotencyKey": "pilot-e2e-key-1"},
    )

    assert retried["id"] == first["id"]


@pytest.mark.asyncio
async def test_agent_tool_creates_a_real_sales_lead_over_http(encore_client: EncoreClient, registry: ToolRegistry):
    workspace_id = await _make_workspace(encore_client, "Pilot E2E Commercial Workspace")

    created = await registry.invoke("lead_create", {"workspaceId": workspace_id, "name": "Pilot Lead"})

    assert created["id"] > 0
    assert created["workspaceId"] == workspace_id
    assert created["stage"] == "NEW"

    listed = await registry.invoke("lead_list", {"workspaceId": workspace_id})
    assert any(lead["id"] == created["id"] for lead in listed["leads"])


@pytest.mark.asyncio
async def test_agent_tool_updates_a_real_sales_lead_stage_over_http(
    encore_client: EncoreClient, registry: ToolRegistry
):
    workspace_id = await _make_workspace(encore_client, "Pilot E2E Commercial Stage Workspace")
    created = await registry.invoke("lead_create", {"workspaceId": workspace_id, "name": "Pilot Lead"})

    updated = await registry.invoke("lead_update_stage", {"id": created["id"], "stage": "QUALIFIED"})

    assert updated["id"] == created["id"]
    assert updated["stage"] == "QUALIFIED"
