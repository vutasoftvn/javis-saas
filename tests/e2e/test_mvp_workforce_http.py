"""End-to-End HTTP Integration Test for Workforce Subsystem."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)


@pytest.fixture
def e2e_app():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        model=FakeSDKModel(),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    return create_cosa_app(plane)


@pytest.mark.asyncio
async def test_full_workforce_lifecycle_e2e(e2e_app) -> None:
    workspace_id = "ws_e2e_workforce"
    override_authenticated_identity(e2e_app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=e2e_app),
        base_url="http://test",
    ) as client:
        # 1. Initially empty roster
        list_res = await client.get("/agent/workforce/assignments")
        assert list_res.status_code == 200
        assert list_res.json()["meta"]["data_state"] == "empty"
        assert list_res.json()["data"] == []

        # 2. Composition initially shows unassigned
        comp_res = await client.get("/agent/workforce/composition")
        assert comp_res.status_code == 200
        catalog = comp_res.json()["data"]
        assert len(catalog) > 0
        assert all(not item["assigned"] for item in catalog)

        # 3. Create assignment for campaign_planner
        create_res = await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner"},
        )
        assert create_res.status_code == 200
        asg = create_res.json()["data"]
        assignment_id = asg["assignment_id"]
        assert asg["functional_key"] == "campaign_planner"
        assert asg["status"] == "ACTIVE"

        # 4. Check active roster now populated
        list_after = await client.get("/agent/workforce/assignments")
        assert list_after.status_code == 200
        assert list_after.json()["meta"]["data_state"] == "populated"
        assert len(list_after.json()["data"]) == 1

        # 5. Capabilities list returns pinned capability prefixes
        cap_res = await client.get("/agent/workforce/capabilities")
        assert cap_res.status_code == 200
        caps = cap_res.json()["data"]
        assert len(caps) > 0
        assert any(c["functional_key"] == "campaign_planner" for c in caps)

        # 6. Health returns not_observed (no runs yet)
        health_res = await client.get("/agent/workforce/health")
        assert health_res.status_code == 200
        health_items = health_res.json()["data"]
        assert len(health_items) == 1
        assert health_items[0]["status"] == "not_observed"

        # 7. Org Chart returns single node tree
        org_res = await client.get("/agent/workforce/org-chart")
        assert org_res.status_code == 200
        org_chart = org_res.json()["data"]
        assert org_chart["total_assignments"] == 1
        assert len(org_chart["roots"]) == 1

        # 8. Schedules list (empty) and create
        sched_list = await client.get("/agent/workforce/schedules")
        assert sched_list.status_code == 200
        assert sched_list.json()["meta"]["data_state"] == "empty"

        sched_create = await client.post(
            "/agent/workforce/schedules",
            json={
                "name": "Daily Campaign Sync",
                "functional_key": "campaign_planner",
                "cron_expression": "0 9 * * *",
            },
        )
        assert sched_create.status_code == 200
        schedule_id = sched_create.json()["data"]["schedule_id"]

        sched_run = await client.post(f"/agent/workforce/schedules/{schedule_id}/run-now")
        assert sched_run.status_code == 200
        assert sched_run.json()["data"]["status"] == "QUEUED"

        # 9. Retire assignment
        retire_res = await client.post(f"/agent/workforce/assignments/{assignment_id}/retire")
        assert retire_res.status_code == 200
        assert retire_res.json()["data"]["status"] == "RETIRED"

        # 10. Check active roster is empty again
        list_retired = await client.get("/agent/workforce/assignments?status=ACTIVE")
        assert list_retired.status_code == 200
        assert list_retired.json()["meta"]["data_state"] == "empty"
