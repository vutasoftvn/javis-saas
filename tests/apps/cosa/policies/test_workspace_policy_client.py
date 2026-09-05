from __future__ import annotations

import httpx
import pytest

from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient, CosaTenantPolicyError


def _client_with_handler(handler) -> CosaTenantPolicyClient:
    return CosaTenantPolicyClient(base_url="http://cosa-control-plane.test", transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_get_snapshot_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/platform/auth/me/agent-policy-snapshot"
        assert request.url.params["workspaceId"] == "c1"
        assert request.headers["authorization"] == "Bearer tok"
        return httpx.Response(
            200,
            json={
                "workspaceId": "c1",
                "workspaceStatus": "active",
                "principalStatus": "active",
                "rules": [{"toolPattern": "finance.*", "decision": "REQUIRE_APPROVAL", "reason": None}],
                "snapshotHash": "abc123",
            },
        )

    client = _client_with_handler(handler)
    snapshot = await client.get_snapshot("tok", "c1")
    assert snapshot.workspace_id == "c1"
    assert snapshot.workspace_status == "active"
    assert len(snapshot.rules) == 1
    assert snapshot.rules[0].tool_pattern == "finance.*"
    assert snapshot.snapshot_hash == "abc123"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_snapshot_403_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "permission_denied"})

    client = _client_with_handler(handler)
    with pytest.raises(CosaTenantPolicyError):
        await client.get_snapshot("tok", "not_my_workspace")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_snapshot_network_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = _client_with_handler(handler)
    with pytest.raises(CosaTenantPolicyError):
        await client.get_snapshot("tok", "c1")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_snapshot_missing_field_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"workspaceId": "c1"})  # thiếu workspaceStatus/rules/...

    client = _client_with_handler(handler)
    with pytest.raises(CosaTenantPolicyError):
        await client.get_snapshot("tok", "c1")
    await client.aclose()


@pytest.mark.asyncio
async def test_evaluate_business_action_targets_company_plane_not_control_plane():
    # IA02: evaluate_business_action phải gọi services/company (Company
    # Business plane), KHÔNG được đi qua self._client (control plane) như
    # get_snapshot — 2 plane khác nhau, khác secret verify.
    control_plane_calls: list[httpx.Request] = []

    def control_plane_handler(request: httpx.Request) -> httpx.Response:
        control_plane_calls.append(request)
        return httpx.Response(500, json={"error": "should not be called"})

    def company_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/identity/business-policy/evaluate"
        assert request.headers["authorization"] == "Bearer company-delegation-jwt"
        assert request.headers["x-workspace-id"] == "ws1"
        return httpx.Response(200, json={"effect": "ALLOW", "reasonCodes": []})

    client = CosaTenantPolicyClient(
        base_url="http://cosa-control-plane.test",
        transport=httpx.MockTransport(control_plane_handler),
        company_base_url="http://company-plane.test",
        company_transport=httpx.MockTransport(company_handler),
    )

    result = await client.evaluate_business_action(
        "company-delegation-jwt",
        "ws1",
        "finance.payment.approve",
    )
    assert result["effect"] == "ALLOW"
    assert control_plane_calls == []  # không lọt sang control plane
    await client.aclose()


@pytest.mark.asyncio
async def test_evaluate_business_action_non_200_raises():
    def company_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "permission_denied"})

    client = CosaTenantPolicyClient(
        base_url="http://cosa-control-plane.test",
        transport=httpx.MockTransport(lambda r: httpx.Response(500)),
        company_base_url="http://company-plane.test",
        company_transport=httpx.MockTransport(company_handler),
    )
    with pytest.raises(CosaTenantPolicyError):
        await client.evaluate_business_action("tok", "ws1", "finance.payment.approve")
    await client.aclose()
