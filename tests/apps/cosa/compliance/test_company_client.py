from __future__ import annotations

from datetime import UTC, datetime

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
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    assert snap.workspace_id == "ws_1"
    assert snap.mode == "ADVISORY_ONLY"
    assert "finance.read" in snap.allowed_capabilities


@pytest.mark.asyncio
async def test_company_client_raises_unavailable_on_connection_error() -> None:
    # Task 4: resolve_snapshot giờ đòi capability_ids + delegation_token
    # (route runtime dùng delegation Task 3, không còn route capture cũ).
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
