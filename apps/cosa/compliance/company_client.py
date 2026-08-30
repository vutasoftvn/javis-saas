from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceSnapshot,
)

# Task 4 — mọi field bên dưới PHẢI có mặt trong response của route runtime
# (services/company/finance-legal/handlers/ai-compliance-runtime.handler.ts).
# Trước Task 4, code cũ dùng `.get(key, default)` để tự điền mode/status/
# provider_profile_version khi thiếu — đây chính là kiểu "fail-open" khiến
# một response thiếu dữ liệu bị hiểu nhầm thành ADVISORY_ONLY/APPROVED_FOR_USE
# giả. Giờ đây field thiếu ⇒ CONTRACT_VIOLATION (fail-closed), không default.
_REQUIRED_FIELDS = (
    "workspaceId",
    "deploymentId",
    "assessmentId",
    "mode",
    "status",
    "allowedCapabilities",
    "providerProfileVersion",
    "dataProfileVersion",
    "snapshotHash",
    "expiresAt",
    # Task 4 — provenance bắt buộc để resolver dựng DataAccessClaim thật từ
    # snapshot (không lấy provider/model/purpose/retention từ đâu khác).
    # Company (Task 2) đã đảm bảo route runtime luôn trả đủ 4 field này khi
    # `provenanceComplete: true`; ở đây bắt buộc lại phía client để fail-
    # closed nếu response cũ/hỏng thiếu field — không default về "" hay None.
    "providerKey",
    "modelKey",
    "purposeId",
    "retentionPolicyId",
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
        capability_ids: list[str],
        delegation_token: str,
        policy_snapshot_hash: str = "",
    ) -> ComplianceSnapshot:
        """Gọi route runtime private (Task 4) — KHÔNG còn gọi route capture
        cũ (`POST /finance-legal/ai-compliance/snapshots`, vốn tự tạo
        deployment/assessment/APPROVED mặc định — lỗ hổng đã xác nhận). Route
        mới CHỈ đọc, dùng delegation có cấu trúc COSA→Company (Task 3) thay vì
        session user, và yêu cầu khai báo đúng tập capability_ids cần dùng.
        """
        url = f"{self._base_url}/finance-legal/ai-compliance/runtime/snapshots/resolve"
        headers = {
            "X-Workspace-Id": str(workspace_id),
            "Authorization": f"Bearer {delegation_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "runId": run_id,
            "systemKey": system_key,
            "capabilityIds": list(capability_ids),
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
            raise AiComplianceUnavailable(
                "NOT_READY", "No approved deployment/capability found for this system"
            )
        if response.status_code == 409:
            raise AiComplianceUnavailable(
                "APPROVAL_INCOMPLETE_OR_EXPIRED",
                "Current approval is incomplete, missing evidence/profiles, or expired",
            )
        if response.status_code == 403:
            raise AiComplianceUnavailable(
                "DELEGATION_DENIED", "Delegation scope check failed at Company"
            )
        if response.status_code != 200:
            raise AiComplianceUnavailable(f"HTTP_{response.status_code}", response.text)

        try:
            data = response.json()
        except Exception as err:
            raise AiComplianceUnavailable(
                "INVALID_RESPONSE", "Invalid JSON from company service"
            ) from err

        if not isinstance(data, dict):
            raise AiComplianceUnavailable("CONTRACT_VIOLATION", "Response is not a JSON object")

        missing = [f for f in _REQUIRED_FIELDS if data.get(f) is None]
        if missing:
            raise AiComplianceUnavailable(
                "CONTRACT_VIOLATION", f"Response missing required field(s): {', '.join(missing)}"
            )

        try:
            expires_at_raw = data["expiresAt"]
            expires_at = (
                datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
                if isinstance(expires_at_raw, str)
                else expires_at_raw
            )

            snapshot = ComplianceSnapshot(
                workspace_id=str(data["workspaceId"]),
                deployment_id=str(data["deploymentId"]),
                assessment_id=str(data["assessmentId"]),
                mode=data["mode"],
                status=data["status"],
                allowed_capabilities=frozenset(data["allowedCapabilities"]),
                provider_profile_version=str(data["providerProfileVersion"]),
                data_profile_version=str(data["dataProfileVersion"]),
                provider_key=str(data["providerKey"]),
                model_key=str(data["modelKey"]),
                purpose_id=str(data["purposeId"]),
                retention_policy_id=str(data["retentionPolicyId"]),
                snapshot_hash=str(data["snapshotHash"]),
                expires_at=expires_at,
                policy_snapshot_hash=str(data.get("policySnapshotHash") or ""),
                evidence_hashes=list(data.get("evidenceHashes") or []),
                rule_version_ids=list(data.get("legalVersionIds") or []),
            )
        except AiComplianceUnavailable:
            raise
        except Exception as err:
            raise AiComplianceUnavailable("CONTRACT_VIOLATION", str(err)) from err

        now = datetime.now(UTC)
        if snapshot.expires_at <= now:
            raise AiComplianceUnavailable(
                "EXPIRED", f"Compliance snapshot expired at {snapshot.expires_at}"
            )

        return snapshot

    async def resolve_data_use(
        self,
        workspace_id: str,
        deployment_id: str,
        capability_id: str,
        purpose_id: str,
        data_categories: list[str] | set[str] | frozenset[str],
        provider_key: str,
        model_key: str = "",
        subject_reference: str | None = None,
        delegation_token: str | None = None,
    ) -> Any:
        url = f"{self._base_url}/finance-legal/ai-compliance/resolve-data-use"
        headers = {
            "X-Workspace-Id": str(workspace_id),
            "Content-Type": "application/json",
        }
        if delegation_token:
            headers["Authorization"] = f"Bearer {delegation_token}"

        payload: dict[str, Any] = {
            "deploymentId": str(deployment_id),
            "capabilityId": capability_id,
            "purposeId": purpose_id,
            "dataCategories": list(data_categories),
            "providerKey": provider_key,
            "modelKey": model_key,
        }
        if subject_reference is not None:
            payload["subjectReference"] = subject_reference

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as err:
            raise AiComplianceUnavailable("CONNECTION_ERROR", str(err)) from err
        except Exception as err:
            raise AiComplianceUnavailable("UNAVAILABLE", str(err)) from err

        if response.status_code != 200:
            raise AiComplianceUnavailable(f"HTTP_{response.status_code}", response.text)

        try:
            data = response.json()
        except Exception as err:
            raise AiComplianceUnavailable("INVALID_RESPONSE", str(err)) from err

        from types import SimpleNamespace

        return SimpleNamespace(
            allowed=data.get("allowed", False),
            denial_code=data.get("denialCode"),
            provider_profile_version=data.get("providerProfileVersion"),
            data_profile_version=data.get("dataProfileVersion"),
            retention_policy_id=data.get("retentionPolicyId"),
            minimization_required=data.get("minimizationRequired", False),
        )

