"""E2E HTTP proof cho Organization API (spec 2026-09-25 §7) trên process Company thật.

Founder đọc được overview/workforce của chính organization; request lệch
header/path, thiếu token, hoặc trỏ tới workspace agent không tồn tại đều bị từ
chối với mã lỗi rõ ràng (Flutter hiển thị lỗi thay vì dữ liệu rỗng).
"""

from __future__ import annotations

import time

import httpx

from tests.e2e.conftest import CompanyServiceHandle


def test_organization_api_contract(real_company_service: CompanyServiceHandle) -> None:
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    registration = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"organization-api-{time.time_ns()}@example.com",
            "displayName": "Organization API Founder",
        },
    )
    assert registration.status_code == 200, registration.text
    session = registration.json()
    org_id = str(session["workspaceId"])
    headers = {
        "Authorization": f"Bearer {session['accessToken']}",
        "X-Workspace-Id": org_id,
    }

    overview = client.get(f"/operations/organizations/{org_id}/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["organizationId"] == org_id
    assert body["canManageWorkforce"] is True

    workforce = client.get(f"/operations/organizations/{org_id}/workforce", headers=headers)
    assert workforce.status_code == 200, workforce.text
    assert isinstance(workforce.json()["members"], list)

    unknown_agent = client.post(
        f"/operations/organizations/{org_id}/ai-workforce",
        json={
            "roleTitle": "Ops Agent",
            "workspaceAgentId": "123456789",
            "idempotencyKey": f"e2e-{time.time_ns()}",
        },
        headers=headers,
    )
    assert unknown_agent.status_code == 404, unknown_agent.text

    mismatch = client.get(
        f"/operations/organizations/{org_id}/overview",
        headers={**headers, "X-Workspace-Id": "1"},
    )
    assert mismatch.status_code == 400, mismatch.text

    anonymous = client.get(f"/operations/organizations/{org_id}/overview")
    assert anonymous.status_code == 401, anonymous.text
