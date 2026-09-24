from __future__ import annotations

import httpx
import pytest

from apps.cosa.policies.profile_locale_client import (
    ProfileLocaleClient,
    ProfileLocaleSnapshot,
    ProfileLocaleUnavailable,
)


def _client_with_handler(handler) -> ProfileLocaleClient:
    return ProfileLocaleClient(
        base_url="http://cosa-control-plane.test",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_get_locale_snapshot_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/platform/auth/me/locale-snapshot"
        assert request.url.params["organizationId"] == "ws-123"
        assert request.headers["authorization"] == "Bearer delegation-token"
        return httpx.Response(
            200,
            json={
                "workspace_id": "ws-123",
                "preferred_locale": "en-US",
            },
        )

    client = _client_with_handler(handler)
    snapshot = await client.get_snapshot("delegation-token", "ws-123")
    assert snapshot == ProfileLocaleSnapshot(workspace_id="ws-123", preferred_locale="en-US")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_locale_snapshot_defaults_to_vi_vn():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "workspace_id": "ws-123",
                "preferred_locale": "vi-VN",
            },
        )

    client = _client_with_handler(handler)
    snapshot = await client.get_snapshot("delegation-token", "ws-123")
    assert snapshot == ProfileLocaleSnapshot(workspace_id="ws-123", preferred_locale="vi-VN")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_locale_snapshot_403_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "permission_denied"})

    client = _client_with_handler(handler)
    with pytest.raises(ProfileLocaleUnavailable):
        await client.get_snapshot("delegation-token", "foreign-ws")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_locale_snapshot_network_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = _client_with_handler(handler)
    with pytest.raises(ProfileLocaleUnavailable):
        await client.get_snapshot("delegation-token", "ws-123")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_locale_snapshot_malformed_locale_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "workspace_id": "ws-123",
                "preferred_locale": "fr-FR",
            },
        )

    client = _client_with_handler(handler)
    with pytest.raises(ProfileLocaleUnavailable):
        await client.get_snapshot("delegation-token", "ws-123")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_locale_snapshot_mismatched_workspace_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "workspace_id": "ws-other-workspace",
                "preferred_locale": "en-US",
            },
        )

    client = _client_with_handler(handler)
    with pytest.raises(ProfileLocaleUnavailable, match="workspace_id mismatch"):
        await client.get_snapshot("delegation-token", "ws-123")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_locale_snapshot_missing_workspace_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "preferred_locale": "en-US",
            },
        )

    client = _client_with_handler(handler)
    with pytest.raises(ProfileLocaleUnavailable, match="workspace_id mismatch or missing"):
        await client.get_snapshot("delegation-token", "ws-123")
    await client.aclose()
