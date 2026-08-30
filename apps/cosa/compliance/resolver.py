from __future__ import annotations

from typing import Any

import jwt as _pyjwt
from agent.contracts.run import RunRequest
from agent.contracts.spec import AgentSpec

from apps.cosa.auth.jwt import mint_company_delegation
from apps.cosa.compliance.company_client import AiComplianceClient
from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceDenied,
)


class ComplianceResolver:
    def __init__(self, client: AiComplianceClient | None = None) -> None:
        self._client = client or AiComplianceClient()

    async def resolve_for_run(
        self,
        request: RunRequest,
        spec: AgentSpec,
    ) -> dict[str, Any]:
        workspace_id = request.workspace_id
        if not workspace_id:
            raise ComplianceDenied(
                "MISSING_WORKSPACE_ID", "Workspace ID is required for AI compliance resolution"
            )

        run_id = getattr(request, "run_id", None) or getattr(request, "id", None) or "run_initial"
        system_key = spec.id

        # Task 4 — capability_ids khai báo đúng tập capability agent này cần
        # dùng (spec.capability_refs), KHÔNG suy đoán/mở rộng. Rỗng ⇒ fail
        # closed ngay ở đây thay vì gọi Company với 1 request rỗng (Company
        # cũng từ chối, nhưng chặn sớm tránh vòng round-trip vô nghĩa và tránh
        # mint 1 delegation token không phạm vi nào).
        capability_ids = list(spec.capability_refs)
        if not capability_ids:
            raise ComplianceDenied(
                "MISSING_CAPABILITIES",
                f"AgentSpec '{spec.id}' declares no capability_refs — cannot scope a compliance delegation",
            )

        policy_snapshot_hash = ""
        if request.metadata:
            policy_snapshot_hash = (
                request.metadata.get("policy_snapshot_ref")
                or request.metadata.get("policy_snapshot_hash")
                or ""
            )

        # Delegation có cấu trúc COSA→Company (Task 3) — điểm wire production
        # đầu tiên (xem task-4-report.md). `sub` là principal đã xác thực của
        # request (KHÔNG phải platform_user_id thô); scope đúng
        # workspace_id + run_id + capability_ids caller khai báo, không hơn.
        delegation_token = mint_company_delegation(
            sub=request.principal,
            workspace_id=workspace_id,
            run_id=run_id,
            capability_ids=capability_ids,
        )

        try:
            snapshot = await self._client.resolve_snapshot(
                workspace_id=workspace_id,
                run_id=run_id,
                system_key=system_key,
                capability_ids=capability_ids,
                delegation_token=delegation_token,
                policy_snapshot_hash=policy_snapshot_hash,
            )
        except AiComplianceUnavailable as err:
            raise ComplianceDenied(err.code, str(err)) from err

        snap_dict = snapshot.model_dump() if hasattr(snapshot, "model_dump") else snapshot
        snap_hash = getattr(snapshot, "snapshot_hash", None) or (
            snap_dict.get("snapshot_hash") if isinstance(snap_dict, dict) else "sha256:mock"
        )
        snap_version = getattr(snapshot, "data_profile_version", None) or (
            snap_dict.get("data_profile_version") if isinstance(snap_dict, dict) else "v1"
        )

        # Task 5 — decode KHÔNG verify chữ ký chỉ để đọc lại claim `jti` của
        # chính token mình vừa mint ở trên (không phải input từ bên ngoài,
        # nên bỏ qua verify signature/exp ở đây là an toàn) — dùng làm
        # `delegation_identity`/`company_delegation_ref`: 1 fingerprint
        # KHÔNG nhạy cảm, an toàn để đưa vào event/audit payload, khác hẳn
        # `_company_delegation_token` (raw JWT) — key có tiền tố `_` báo hiệu
        # caller (worker/kernel) phải tự loại field này trước khi serialize
        # bất kỳ phần nào của RunRequest.metadata vào event/audit.
        try:
            unverified = _pyjwt.decode(delegation_token, options={"verify_signature": False})
            delegation_ref = unverified.get("jti") or "unknown"
        except Exception:
            delegation_ref = "unknown"

        return {
            "compliance_snapshot": snap_dict,
            "compliance_snapshot_ref": snap_hash,
            "compliance_snapshot_version": snap_version,
            "company_delegation_ref": delegation_ref,
            "_company_delegation_token": delegation_token,
        }
