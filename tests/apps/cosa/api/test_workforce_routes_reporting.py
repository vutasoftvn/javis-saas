from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.test_workforce_routes import test_app  # noqa: F401  (fixture dùng chung)


@pytest.mark.asyncio
async def test_reporting_line_is_validated_by_route(test_app) -> None:  # noqa: F811
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        parent = await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner", "company_workforce_member_id": "mem_test"},
        )
        assert parent.status_code == 200
        parent_id = parent.json()["data"]["assignment_id"]

        child = await client.post(
            "/agent/workforce/assignments",
            json={
                "functional_key": "compliance_analyst",
                "company_workforce_member_id": "mem_test",
                "reports_to_assignment_id": parent_id,
            },
        )
        assert child.status_code == 200
        assert child.json()["data"]["reports_to_assignment_id"] == parent_id

        bad = await client.post(
            "/agent/workforce/assignments",
            json={
                "functional_key": "compliance_analyst",
                "company_workforce_member_id": "mem_test",
                "reports_to_assignment_id": str(uuid4()),
            },
        )
        assert bad.status_code == 422
        assert bad.json()["detail"]["code"] == "reporting_line_parent_not_found"


@pytest.mark.asyncio
async def test_org_chart_warns_when_manager_is_not_active(test_app) -> None:  # noqa: F811
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        parent = await client.post(
            "/agent/workforce/assignments",
            json={"functional_key": "campaign_planner", "company_workforce_member_id": "mem_test"},
        )
        parent_id = parent.json()["data"]["assignment_id"]
        child = await client.post(
            "/agent/workforce/assignments",
            json={
                "functional_key": "compliance_analyst",
                "company_workforce_member_id": "mem_test",
                "reports_to_assignment_id": parent_id,
            },
        )
        child_id = child.json()["data"]["assignment_id"]

        healthy = (await client.get("/agent/workforce/org-chart")).json()["data"]
        assert [n["assignment_id"] for n in healthy["roots"]] == [parent_id]
        assert healthy["roots"][0]["warning"] is None
        assert healthy["roots"][0]["direct_reports"][0]["warning"] is None

        retired = await client.post(f"/agent/workforce/assignments/{parent_id}/retire")
        assert retired.status_code == 200

        chart = (await client.get("/agent/workforce/org-chart")).json()["data"]
        assert [n["assignment_id"] for n in chart["roots"]] == [child_id]
        assert chart["roots"][0]["warning"] == "manager_not_active"
