from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

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
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


@pytest.fixture
def test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
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
async def test_empty_assignment_roster_is_honest(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/assignments")
        assert res.status_code == 200
        data = res.json()
        assert data["meta"]["data_state"] == "empty"
        assert data["data"] == []


@pytest.mark.asyncio
async def test_create_assignment_and_list(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        create_res = await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner"},
        )
        assert create_res.status_code == 200
        created = create_res.json()["data"]
        assert created["functional_key"] == "campaign_planner"
        assert created["status"] == "ACTIVE"
        assert created["workspace_id"] == "ws_1001"

        list_res = await client.get("/agent/workforce/assignments")
        assert list_res.status_code == 200
        items = list_res.json()["data"]
        assert len(items) == 1
        assert items[0]["assignment_id"] == created["assignment_id"]


@pytest.mark.asyncio
async def test_tenant_isolation_cannot_see_or_retire_other_workspace_assignment(test_app) -> None:
    # 1. Workspace A creates an assignment
    override_authenticated_identity(test_app, workspace_id="ws_A", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client_a:
        res_a = await client_a.post(
            "/agent/workforce/assignments",
            json={"functional_key": "compliance_analyst"},
        )
        assert res_a.status_code == 200
        assignment_id_a = res_a.json()["data"]["assignment_id"]

    # 2. Workspace B lists assignments (must not see Workspace A's assignment)
    override_authenticated_identity(test_app, workspace_id="ws_B", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client_b:
        res_b = await client_b.get("/agent/workforce/assignments")
        assert res_b.status_code == 200
        assert res_b.json()["data"] == []

        # 3. Workspace B attempts to retire Workspace A's assignment (must fail with 404)
        retire_b = await client_b.post(f"/agent/workforce/assignments/{assignment_id_a}/retire")
        assert retire_b.status_code == 404


@pytest.mark.asyncio
async def test_composition_shows_assigned_status_honestly(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        # Initially, all are unassigned
        comp_res = await client.get("/agent/workforce/composition")
        assert comp_res.status_code == 200
        entries = comp_res.json()["data"]
        assert len(entries) > 0
        assert all(not e["assigned"] for e in entries)

        # Assign campaign_planner
        await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner"},
        )

        comp_after = await client.get("/agent/workforce/composition")
        entries_after = comp_after.json()["data"]
        cp_entry = next(e for e in entries_after if e["functional_key"] == "campaign_planner")
        assert cp_entry["assigned"] is True


@pytest.mark.asyncio
async def test_health_reports_not_observed_when_no_runs(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner"},
        )
        health_res = await client.get("/agent/workforce/health")
        assert health_res.status_code == 200
        items = health_res.json()["data"]
        assert len(items) == 1
        assert items[0]["status"] == "not_observed"
        assert items[0]["observed_at"] is None


@pytest.mark.asyncio
async def test_workforce_approvals_use_mvp_envelope(test_app) -> None:
    """Task 3: GET /agent/workforce/approvals phải trả đúng MVP envelope
    {data, meta} — không được trả object thô {items, total} trái contract
    mà mọi consumer MvpRequestClient khác đang giả định."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/agent/workforce/approvals")
        assert response.status_code == 200
        assert set(response.json()) == {"data", "meta"}


@pytest.mark.asyncio
async def test_workspace_b_cannot_decide_workspace_a_approval(test_app) -> None:
    """Workspace B không được phép quyết định approval thuộc workspace A —
    approval_id không tự mang tenant scope, phải tra run liên kết trước khi
    cho quyết định (xem test_tenant_b_cannot_decide_approval_of_tenant_a_run
    trong test_tenant_isolation.py cho biến thể qua run thật)."""
    from agent.runs.models import RunRecord

    override_authenticated_identity(test_app, workspace_id="ws_A", role_id="founder")
    plane = test_app.state.plane
    run = RunRecord(
        company_id="ws_A",
        workspace_id="ws_A",
        principal="user:alice",
        root_executable_id="test-spec",
    )
    await plane.repository.create_run(run)

    approval, _wait_desc = await plane.approval_service.create_approval_request(
        run_id=run.run_id,
        tool_call_id="tc_1",
        checkpoint_ref="ckpt_1",
        requirement={"risk_level": "high"},
        requester="user:alice",
        action="finance.wire_payout",
        subject="Acme Corp",
    )

    override_authenticated_identity(test_app, workspace_id="ws_B", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client_b:
        response = await client_b.post(
            f"/agent/workforce/approvals/{approval.approval_id}/decision",
            json={"approved": True, "reason": "not allowed"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_empty_schedule_list_is_honest(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/schedules")
        assert res.status_code == 200
        data = res.json()
        assert data["meta"]["data_state"] == "empty"
        assert data["data"] == []


@pytest.mark.asyncio
async def test_create_schedule_persists_and_lists(test_app) -> None:
    """P0.2 — trước fix, create_schedule dựng response in-memory không ghi
    DB: GET sau đó vẫn trả rỗng. Test này chứng minh dữ liệu còn tồn tại sau
    khi tạo, không chỉ response ban đầu hợp lệ schema."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        create_res = await client.post(
            "/agent/workforce/schedules",
            json={
                "name": "Weekly cashflow review",
                "functional_key": "cashflow_planner",
                "cron_expression": "0 9 * * 1",
            },
        )
        assert create_res.status_code == 200
        created = create_res.json()["data"]
        assert created["functional_key"] == "cashflow_planner"
        assert created["status"] == "ACTIVE"
        assert created["workspace_id"] == "ws_1001"

        list_res = await client.get("/agent/workforce/schedules")
        assert list_res.status_code == 200
        items = list_res.json()["data"]
        assert len(items) == 1
        assert items[0]["schedule_id"] == created["schedule_id"]


@pytest.mark.asyncio
async def test_create_schedule_rejects_unknown_functional_key(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.post(
            "/agent/workforce/schedules",
            json={
                "name": "Bogus",
                "functional_key": "does_not_exist_in_catalog",
                "cron_expression": "0 9 * * 1",
            },
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_schedule_tenant_isolation(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_A", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client_a:
        await client_a.post(
            "/agent/workforce/schedules",
            json={
                "name": "A's schedule",
                "functional_key": "cashflow_planner",
                "cron_expression": "0 9 * * 1",
            },
        )

    override_authenticated_identity(test_app, workspace_id="ws_B", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client_b:
        res = await client_b.get("/agent/workforce/schedules")
        assert res.json()["data"] == []


@pytest.mark.asyncio
async def test_run_schedule_now_reports_not_implemented_instead_of_fake_success(
    test_app,
) -> None:
    """P0.2 — trước fix, run-now luôn trả status=QUEUED giả cho bất kỳ
    schedule_id nào (kể cả không tồn tại), không dispatch gì thật. Sau fix:
    404 nếu schedule không tồn tại trong workspace, 501 rõ ràng nếu tồn tại
    nhưng chưa hỗ trợ thực thi — không còn giả vờ thành công."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        missing_res = await client.post("/agent/workforce/schedules/does-not-exist/run-now")
        assert missing_res.status_code == 404

        create_res = await client.post(
            "/agent/workforce/schedules",
            json={
                "name": "Weekly cashflow review",
                "functional_key": "cashflow_planner",
                "cron_expression": "0 9 * * 1",
            },
        )
        schedule_id = create_res.json()["data"]["schedule_id"]

        run_now_res = await client.post(f"/agent/workforce/schedules/{schedule_id}/run-now")
        assert run_now_res.status_code == 501


@pytest.mark.asyncio
async def test_roster_lists_functional_catalog_with_default_available_status(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/roster")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 6  # FUNCTIONAL_AGENT_CATALOG has 6 entries today
        cashflow = next(e for e in data if e["key"] == "cashflow_planner")
        assert cashflow["name"] == "Cashflow Planner"
        assert cashflow["department"] == "Finance"
        assert cashflow["status"] == "available"
        assert cashflow["enabled"] is True


@pytest.mark.asyncio
async def test_roster_marks_assigned_entries_active(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        create_res = await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner"},
        )
        assert create_res.status_code == 200

        res = await client.get("/agent/workforce/roster")
        assert res.status_code == 200
        entry = next(e for e in res.json()["data"] if e["key"] == "campaign_planner")
        assert entry["status"] == "active"


@pytest.mark.asyncio
async def test_work_products_maps_workspace_artifacts(test_app) -> None:
    from agent.artifacts.models import WorkspaceArtifact
    from agent.contracts.run import RunStatus
    from agent.runs.models import RunRecord

    plane = test_app.state.plane
    run = RunRecord(
        run_id="run_wp_1",
        workspace_id="ws_1001",
        principal="user:founder",
        root_executable_id="functional.market_research_specialist",
        status=RunStatus.COMPLETED,
    )
    await plane.repository.create_run(run)
    await plane.artifact_repository.create(
        WorkspaceArtifact(
            workspace_id="ws_1001",
            conversation_id="conv_1",
            run_id="run_wp_1",
            display_name="Market brief Q1",
            media_type="text/markdown",
            object_ref="object://brief-q1",
        )
    )

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/artifacts")
        assert res.status_code == 200
        items = res.json()["data"]
        assert len(items) == 1
        item = items[0]
        assert item["title"] == "Market brief Q1"
        assert item["product_type"] == "text/markdown"
        assert item["status"] == "READY"
        assert item["author_agent_key"] == "functional.market_research_specialist"
        assert item["object_ref"] == "object://brief-q1"


@pytest.mark.asyncio
async def test_work_products_author_unknown_when_run_outside_window(test_app) -> None:
    from agent.artifacts.models import WorkspaceArtifact

    plane = test_app.state.plane
    await plane.artifact_repository.create(
        WorkspaceArtifact(
            workspace_id="ws_1001",
            conversation_id="conv_1",
            run_id="run_not_seeded",
            display_name="Orphan artifact",
            media_type="text/markdown",
            object_ref="object://orphan",
        )
    )

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/artifacts")
        assert res.json()["data"][0]["author_agent_key"] == "unknown"


@pytest.mark.asyncio
async def test_exceptions_lists_failed_runs_as_open(test_app) -> None:
    from agent.contracts.run import RunStatus
    from agent.runs.models import RunRecord

    plane = test_app.state.plane
    await plane.repository.create_run(
        RunRecord(
            run_id="run_failed_1",
            workspace_id="ws_1001",
            principal="user:founder",
            root_executable_id="functional.cashflow_planner",
            status=RunStatus.FAILED,
        )
    )
    await plane.repository.create_run(
        RunRecord(
            run_id="run_ok_1",
            workspace_id="ws_1001",
            principal="user:founder",
            root_executable_id="functional.cashflow_planner",
            status=RunStatus.COMPLETED,
        )
    )

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/exceptions")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total"] == 1
        assert data["founder_gate_count"] == 0
        assert data["has_critical"] is False
        assert data["escalations"][0]["id"] == "run_failed_1"
        assert data["escalations"][0]["exception_type"] == "run_failed"
        assert data["escalations"][0]["tier"] == "LEAD_NOTIFY"
        assert data["escalations"][0]["status"] == "OPEN"


@pytest.mark.asyncio
async def test_exceptions_empty_when_no_failed_runs(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/exceptions")
        assert res.status_code == 200
        assert res.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_stage_roster_proxies_company_and_reshapes(test_app, monkeypatch) -> None:
    async def fake_fetch_stage_roster(workspace_id: str, stage_code: str, principal: str):
        assert workspace_id == "ws_1001"
        assert stage_code == "P2"
        return {
            "stage": {"stageCode": "P2", "taskCount": 1},
            "roster": [
                {
                    "taskId": "t1",
                    "title": "Ship pricing page",
                    "priority": "high",
                    "status": "todo",
                    "projectId": "proj_1",
                }
            ],
            "summary": {"total": 1, "highPriority": 1, "medium": 0, "locked": 0},
        }

    import apps.cosa.api.workforce_routes as workforce_routes_mod

    monkeypatch.setattr(workforce_routes_mod, "_fetch_company_stage_roster", fake_fetch_stage_roster)

    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/workforce/stage-roster/P2")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["stage"]["stage_code"] == "P2"
        assert data["roster"][0]["task_id"] == "t1"
        assert data["summary"]["high_priority"] == 1
