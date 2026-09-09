"""HTTP-level test cho apps/cosa/api/workforce_internal_routes.py (Task 3):
internal eligibility lookup — service-token auth, trả facts (không credential),
fail closed khi employee/assignment không tồn tại hoặc không ACTIVE."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from fastapi.testclient import TestClient

from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane

TOKEN_HEADER = {"X-Workforce-Authz-Token": "dev-workforce-authz-token"}


@pytest_asyncio.fixture
async def client_and_repo():
    repo = InMemoryWorkforceRepository()
    company = AsyncMock(spec=CompanyServiceClient)
    plane = build_cosa_agent_plane(
        company_client=company,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        workforce_repository=repo,
    )
    app = create_cosa_app(plane=plane)
    return TestClient(app), repo


@pytest.mark.asyncio
async def test_eligibility_returns_facts_for_active_employee_with_assignment(client_and_repo):
    client, repo = client_and_repo
    emp = await repo.create_employee("ws_1", "AGT-OPS-001", "Ops #1", "founder")
    asg = await repo.create_assignment(
        workspace_id="ws_1",
        functional_key="operations",
        spec_id="cosa.agents.operations",
        spec_version="1.0.0",
        definition_hash="sha256:ops",
        configured_by="founder",
        agent_instance_id=emp.agent_instance_id,
    )

    resp = client.post(
        "/agent/internal/workforce/eligibility",
        headers=TOKEN_HEADER,
        json={
            "workspace_id": "ws_1",
            "agent_instance_id": str(emp.agent_instance_id),
            "required_capability_refs": ["operations.task.read"],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["agent_instance_id"] == str(emp.agent_instance_id)
    assert data["assignment_id"] == str(asg.assignment_id)
    assert data["status"] == "ACTIVE"
    assert data["spec_snapshot"]["spec_id"] == "cosa.agents.operations"
    assert data["capacity_available"] is True
    # Không lộ secret/token/prompt.
    assert not any(k in data for k in ("token", "secret", "prompt", "credential"))


@pytest.mark.asyncio
async def test_eligibility_requires_service_token(client_and_repo):
    client, _ = client_and_repo
    resp = client.post(
        "/agent/internal/workforce/eligibility",
        json={"workspace_id": "ws_1", "agent_instance_id": "x"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_eligibility_404_for_unknown_or_unassigned_employee(client_and_repo):
    client, repo = client_and_repo
    # Unknown employee.
    r1 = client.post(
        "/agent/internal/workforce/eligibility",
        headers=TOKEN_HEADER,
        json={"workspace_id": "ws_1", "agent_instance_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r1.status_code == 404

    # Known employee but no ACTIVE assignment linked.
    emp = await repo.create_employee("ws_1", "AGT-OPS-002", "Ops #2", "founder")
    r2 = client.post(
        "/agent/internal/workforce/eligibility",
        headers=TOKEN_HEADER,
        json={"workspace_id": "ws_1", "agent_instance_id": str(emp.agent_instance_id)},
    )
    assert r2.status_code == 404
