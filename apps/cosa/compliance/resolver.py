from __future__ import annotations

from typing import Any

import jwt as _pyjwt
from agent.contracts.run import RunRequest
from agent.contracts.spec import AgentSpec

from pydantic import ValidationError

from apps.cosa.auth.jwt import mint_company_delegation
from apps.cosa.compliance.company_client import AiComplianceClient
from apps.cosa.compliance.contracts import (
    AiComplianceUnavailable,
    ComplianceDenied,
)
from apps.cosa.compliance.data_access_claim import DataAccessClaim
from apps.cosa.compliance.data_egress_context import DirectMessageDataAccess

# Snapshot phải cung cấp đủ 4 field này để resolver dựng DataAccessClaim —
# provider/model/purpose/retention LUÔN lấy từ snapshot đã Company duyệt,
# không bao giờ lấy từ context caller khai báo (xem data_egress_context.py).
_CLAIM_PROVENANCE_FIELDS = ("provider_key", "model_key", "purpose_id", "retention_policy_id")


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

        # capability_refs chỉ là executable tools. Direct model input có
        # scope riêng, vẫn phải được Company approve nhưng không được kernel
        # dựng thành tool. Tránh append lần hai nếu một spec cũ đã khai báo
        # nhầm cùng scope trong capability_refs.
        capability_ids = list(
            dict.fromkeys(
                capability_id
                for capability_id in spec.capability_refs
                if capability_id != spec.model_input_capability_ref
            )
        )
        capability_ids.append(spec.model_input_capability_ref)

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

        result: dict[str, Any] = {
            "compliance_snapshot": snap_dict,
            "compliance_snapshot_ref": snap_hash,
            "compliance_snapshot_version": snap_version,
            "company_delegation_ref": delegation_ref,
            "_company_delegation_token": delegation_token,
        }

        # Task 4 — Data Egress Context: nếu caller đã khai báo
        # `direct_message_data_access` trong metadata (Task 5 sẽ là nơi tạo
        # ra field này từ 1 request HTTP thật; ở Task 4 field này chỉ CÓ THỂ
        # có mặt nếu 1 caller thật đã set nó — chưa bắt buộc luôn phải có),
        # dựng `DataAccessClaim` thật để `CosaDataModelGate` không còn phải
        # deny DATA_ACCESS_CLAIM_MISSING. Provider/model/purpose/retention
        # LUÔN lấy từ snapshot vừa được Company duyệt — KHÔNG bao giờ lấy từ
        # context caller khai báo, để tránh 1 caller tự xưng provider/model
        # khác với cái Company đã approve.
        raw_direct_access = (request.metadata or {}).get("direct_message_data_access")
        if raw_direct_access is not None:
            direct_access = self._coerce_direct_message_data_access(raw_direct_access)

            if not spec.model_input_capability_ref:
                raise ComplianceDenied(
                    "DATA_ACCESS_CLAIM_MISSING",
                    "DATA_ACCESS_CLAIM_MISSING: AgentSpec is missing "
                    "model_input_capability_ref — cannot scope a data access claim",
                )

            missing_provenance = [
                field_name
                for field_name in _CLAIM_PROVENANCE_FIELDS
                if not getattr(snapshot, field_name, None)
            ]
            if missing_provenance:
                raise ComplianceDenied(
                    "DATA_ACCESS_CLAIM_MISSING",
                    "DATA_ACCESS_CLAIM_MISSING: compliance snapshot is missing "
                    f"provenance field(s): {', '.join(missing_provenance)}",
                )

            result["data_access_claim"] = DataAccessClaim(
                workspace_id=workspace_id,
                deployment_id=snapshot.deployment_id,
                capability_id=spec.model_input_capability_ref,
                source_ref=direct_access.source_ref,
                source_hash=direct_access.source_hash,
                categories=direct_access.categories,
                purpose_id=snapshot.purpose_id,
                subject_reference=direct_access.subject_reference,
                provider_key=snapshot.provider_key,
                model_key=snapshot.model_key,
                retention_policy_id=snapshot.retention_policy_id,
            )

        return result

    @staticmethod
    def _coerce_direct_message_data_access(raw: Any) -> DirectMessageDataAccess:
        """`request.metadata` là `dict[str, Any]` tự do — Task 5 (HTTP layer)
        sẽ đặt vào đây 1 `DirectMessageDataAccess` đã dựng sẵn, nhưng bất kỳ
        caller nào serialize qua JSON/dict trước cũng phải được coi trọng
        như nhau. Dict không hợp lệ (category rỗng, PERSONAL thiếu
        subject_reference, ...) ⇒ fail-closed, không im lặng bỏ qua."""
        if isinstance(raw, DirectMessageDataAccess):
            return raw
        if isinstance(raw, dict):
            try:
                return DirectMessageDataAccess(**raw)
            except ValidationError as err:
                raise ComplianceDenied(
                    "DATA_ACCESS_CLAIM_MISSING", f"DATA_ACCESS_CLAIM_MISSING: {err}"
                ) from err
        raise ComplianceDenied(
            "DATA_ACCESS_CLAIM_MISSING",
            f"DATA_ACCESS_CLAIM_MISSING: unsupported direct_message_data_access type "
            f"{type(raw).__name__}",
        )
