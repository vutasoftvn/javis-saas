from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceSnapshot,
)


class AiComplianceClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = (
            base_url or os.getenv("COMPANY_SERVICE_URL") or "http://127.0.0.1:4000"
        ).rstrip("/")
        self._timeout = timeout

    async def resolve_snapshot(
        self,
        workspace_id: str,
        run_id: str,
        system_key: str,
        policy_snapshot_hash: str | None = None,
    ) -> ComplianceSnapshot:
        url = f"{self._base_url}/finance-legal/ai-compliance/snapshots"
        headers = {
            "X-Workspace-Id": str(workspace_id),
            "Content-Type": "application/json",
        }
        payload = {
            "runId": run_id,
            "systemKey": system_key,
            "policySnapshotHash": policy_snapshot_hash,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as err:
            raise AiComplianceUnavailable("CONNECTION_ERROR", str(err)) from err
        except Exception as err:
            raise AiComplianceUnavailable("UNAVAILABLE", str(err)) from err

        if response.status_code == 404:
            raise AiComplianceUnavailable("NOT_READY", "Snapshot or deployment not ready")
        if response.status_code != 200:
            raise AiComplianceUnavailable(f"HTTP_{response.status_code}", response.text)

        try:
            data = response.json()
        except Exception as err:
            raise AiComplianceUnavailable(
                "INVALID_RESPONSE", "Invalid JSON from company service"
            ) from err

        try:
            expires_at = data.get("expiresAt") or data.get("expires_at")
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

            snapshot = ComplianceSnapshot(
                workspace_id=str(data.get("workspaceId") or data.get("workspace_id")),
                deployment_id=str(data.get("deploymentId") or data.get("deployment_id")),
                assessment_id=str(data.get("assessmentId") or data.get("assessment_id")),
                mode=data.get("mode", "ADVISORY_ONLY"),
                status=data.get("status", "APPROVED_FOR_USE"),
                allowed_capabilities=frozenset(
                    data.get("allowedCapabilities") or data.get("allowed_capabilities") or []
                ),
                provider_profile_version=str(
                    data.get("providerProfileVersion")
                    or data.get("provider_profile_version")
                    or "1.0.0"
                ),
                data_profile_version=str(
                    data.get("dataProfileVersion") or data.get("data_profile_version") or "1.0.0"
                ),
                snapshot_hash=str(data.get("snapshotHash") or data.get("snapshot_hash")),
                expires_at=expires_at,
            )
        except Exception as err:
            raise AiComplianceUnavailable("CONTRACT_VIOLATION", str(err)) from err

        now = datetime.now(UTC)
        if snapshot.expires_at <= now:
            raise AiComplianceUnavailable(
                "EXPIRED", f"Compliance snapshot expired at {snapshot.expires_at}"
            )

        return snapshot
