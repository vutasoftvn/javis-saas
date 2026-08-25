from __future__ import annotations

import httpx
import pytest

from apps.cosa.auth.cosa_client import CosaControlPlaneAuthClient, CosaControlPlaneAuthError


def _client_with_handler(handler) -> CosaControlPlaneAuthClient:
    transport = httpx.MockTransport(handler)
    return CosaControlPlaneAuthClient(base_url="http://cosa-control-plane.test", transport=transport)


@pytest.mark.asyncio
async def test_list_my_companies_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/platform/auth/me/companies"
        assert request.headers["authorization"] == "Bearer tok123"
        return httpx.Response(200, json={"companies": [{"company_id": "c1", "name": "Acme", "role_id": "founder"}]})

    client = _client_with_handler(handler)
    result = await client.list_my_companies("tok123")
    assert len(result) == 1
    assert result[0].company_id == "c1"
    assert result[0].role_id == "founder"
    await client.aclose()


@pytest.mark.asyncio
async def test_list_my_companies_401_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthenticated"})

    client = _client_with_handler(handler)
    with pytest.raises(CosaControlPlaneAuthError):
        await client.list_my_companies("bad-token")
    await client.aclose()


@pytest.mark.asyncio
async def test_list_my_companies_5xx_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    client = _client_with_handler(handler)
    with pytest.raises(CosaControlPlaneAuthError):
        await client.list_my_companies("tok123")
    await client.aclose()


@pytest.mark.asyncio
async def test_list_my_companies_network_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = _client_with_handler(handler)
    with pytest.raises(CosaControlPlaneAuthError):
        await client.list_my_companies("tok123")
    await client.aclose()


@pytest.mark.asyncio
async def test_list_my_companies_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"companies": []})

    client = _client_with_handler(handler)
    result = await client.list_my_companies("tok123")
    assert result == []
    await client.aclose()
