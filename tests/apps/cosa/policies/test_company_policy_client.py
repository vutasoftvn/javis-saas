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
        assert request.url.params["companyId"] == "c1"
        assert request.headers["authorization"] == "Bearer tok"
        return httpx.Response(
            200,
            json={
                "companyId": "c1",
                "companyStatus": "active",
                "principalStatus": "active",
                "rules": [{"toolPattern": "finance.*", "decision": "REQUIRE_APPROVAL", "reason": None}],
                "snapshotHash": "abc123",
            },
        )

    client = _client_with_handler(handler)
    snapshot = await client.get_snapshot("tok", "c1")
    assert snapshot.company_id == "c1"
    assert snapshot.company_status == "active"
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
        await client.get_snapshot("tok", "not_my_company")
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
        return httpx.Response(200, json={"companyId": "c1"})  # thiếu companyStatus/rules/...

    client = _client_with_handler(handler)
    with pytest.raises(CosaTenantPolicyError):
        await client.get_snapshot("tok", "c1")
    await client.aclose()
