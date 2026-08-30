from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from apps.cosa.compliance.company_client import AiComplianceClient
from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceSnapshot,
)


def test_compliance_snapshot_model_validation() -> None:
    now = datetime.now(UTC)
    snap = ComplianceSnapshot(
        workspace_id="ws_1",
        deployment_id="dep_1",
        assessment_id="ass_1",
        mode="ADVISORY_ONLY",
        status="APPROVED_FOR_USE",
        allowed_capabilities=frozenset(["finance.read"]),
        provider_profile_version="v3",
        data_profile_version="v1",
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    assert snap.workspace_id == "ws_1"
    assert snap.mode == "ADVISORY_ONLY"
    assert "finance.read" in snap.allowed_capabilities


@pytest.mark.asyncio
async def test_company_client_raises_unavailable_on_connection_error() -> None:
    client = AiComplianceClient(base_url="http://127.0.0.1:59999")
    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            "ws_1",
            "run_1",
            "cosa-advisory",
            capability_ids=["finance.read"],
            delegation_token="test-delegation-token",
        )
    assert exc_info.value.code in ("CONNECTION_ERROR", "NOT_READY", "UNAVAILABLE")


def _valid_server_response_dict(**overrides: Any) -> dict[str, Any]:
    expiry = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    base = {
        "workspaceId": "ws_1",
        "deploymentId": "dep_1",
        "assessmentId": "ass_1",
        "mode": "ADVISORY_ONLY",
        "status": "APPROVED_FOR_USE",
        "allowedCapabilities": ["finance.read"],
        "providerProfileVersion": "v3",
        "dataProfileVersion": "v1",
        "providerKey": "deepseek",
        "modelKey": "deepseek-chat",
        "purposeId": "advisory",
        "retentionPolicyId": "retain-30d",
        "snapshotHash": "sha256:validhash123",
        "expiresAt": expiry,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_resolve_snapshot_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_requests: list[httpx.Request] = []

    async def fake_send(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=_valid_server_response_dict(), request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)

    client = AiComplianceClient(base_url="http://company.internal")
    snapshot = await client.resolve_snapshot(
        workspace_id="ws_1",
        run_id="run_100",
        system_key="cosa-advisory",
        capability_ids=["finance.read"],
        delegation_token="delegation-secret-jwt",
        policy_snapshot_hash="policy-hash-456",
    )

    assert isinstance(snapshot, ComplianceSnapshot)
    assert snapshot.workspace_id == "ws_1"
    assert snapshot.deployment_id == "dep_1"
    assert snapshot.status == "APPROVED_FOR_USE"
    assert "finance.read" in snapshot.allowed_capabilities

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers["X-Workspace-Id"] == "ws_1"
    assert req.headers["Authorization"] == "Bearer delegation-secret-jwt"
    import json
    body = json.loads(req.content)
    assert body["runId"] == "run_100"
    assert body["systemKey"] == "cosa-advisory"
    assert body["capabilityIds"] == ["finance.read"]
    assert body["policySnapshotHash"] == "policy-hash-456"


@pytest.mark.asyncio
async def test_resolve_snapshot_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_send(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(404, text="Not Found", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)

    client = AiComplianceClient(base_url="http://company.internal")
    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id="ws_1",
            run_id="run_1",
            system_key="unknown-sys",
            capability_ids=["finance.read"],
            delegation_token="token",
        )
    assert exc_info.value.code == "NOT_READY"


@pytest.mark.asyncio
async def test_resolve_snapshot_conflict_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_send(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(409, text="Conflict / Incomplete", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)

    client = AiComplianceClient(base_url="http://company.internal")
    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id="ws_1",
            run_id="run_1",
            system_key="cosa-advisory",
            capability_ids=["finance.read"],
            delegation_token="token",
        )
    assert exc_info.value.code == "APPROVAL_INCOMPLETE_OR_EXPIRED"


@pytest.mark.asyncio
async def test_resolve_snapshot_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_send(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(403, text="Forbidden", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)

    client = AiComplianceClient(base_url="http://company.internal")
    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id="ws_1",
            run_id="run_1",
            system_key="cosa-advisory",
            capability_ids=["finance.read"],
            delegation_token="token",
        )
    assert exc_info.value.code == "DELEGATION_DENIED"


@pytest.mark.asyncio
async def test_resolve_snapshot_contract_violation_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    # Response lacks 'snapshotHash' and 'dataProfileVersion'
    incomplete = _valid_server_response_dict()
    del incomplete["snapshotHash"]
    del incomplete["dataProfileVersion"]

    async def fake_send(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json=incomplete, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)

    client = AiComplianceClient(base_url="http://company.internal")
    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id="ws_1",
            run_id="run_1",
            system_key="cosa-advisory",
            capability_ids=["finance.read"],
            delegation_token="token",
        )
    assert exc_info.value.code == "CONTRACT_VIOLATION"


@pytest.mark.asyncio
async def test_missing_provider_key_is_a_contract_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4 — provenance field thiếu (providerKey) phải fail-closed với
    CONTRACT_VIOLATION, không rơi về snapshot thiếu provider/model để
    resolver sau đó dựng DataAccessClaim sai."""
    incomplete = _valid_server_response_dict()
    del incomplete["providerKey"]

    async def fake_send(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json=incomplete, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)

    client = AiComplianceClient(base_url="http://company.internal")
    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id="ws_1",
            run_id="run_1",
            system_key="cosa-advisory",
            capability_ids=["finance.read"],
            delegation_token="token",
        )
    assert exc_info.value.code == "CONTRACT_VIOLATION"
    assert "providerKey" in str(exc_info.value)


@pytest.mark.asyncio
async def test_resolve_snapshot_expired_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    expired_resp = _valid_server_response_dict(expiresAt=past)

    async def fake_send(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json=expired_resp, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)

    client = AiComplianceClient(base_url="http://company.internal")
    with pytest.raises(AiComplianceUnavailable) as exc_info:
        await client.resolve_snapshot(
            workspace_id="ws_1",
            run_id="run_1",
            system_key="cosa-advisory",
            capability_ids=["finance.read"],
            delegation_token="token",
        )
    assert exc_info.value.code == "EXPIRED"
