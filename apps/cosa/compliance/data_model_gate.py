from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.cosa.compliance.contracts import ComplianceDenied
from apps.cosa.compliance.data_access_claim import DataAccessClaim
from apps.cosa.compliance.redaction import Redactor


class CosaDataModelGate:
    def __init__(
        self,
        client: Any = None,
        redactor: Redactor | None = None,
    ) -> None:
        self._client = client
        self._redactor = redactor or Redactor()

    async def prepare_initial_input(self, run_context: Mapping[str, Any], raw_input: str) -> str:
        claim: DataAccessClaim | None = run_context.get("data_access_claim")
        if claim is None and "claim" in run_context:
            raw_c = run_context["claim"]
            if isinstance(raw_c, DataAccessClaim):
                claim = raw_c

        # Task 7 audit (2026-08-30) — con đường DUY NHẤT sản xuất
        # (`apps.cosa.composition.agent_plane.build_cosa_agent_plane`, runtime
        # "openai_agents" mặc định) LUÔN wire `CosaDataModelGate` cùng lúc với
        # `compliance_resolver` — tức MỌI lần gate này chạy với `self._client`
        # khác `None` đều là 1 run compliance-gated thật (không tồn tại
        # đường chạy "openai_agents runtime nhưng bỏ qua compliance" nào khác
        # — xác nhận bằng đọc agent_plane.py dòng ~607-624). Vì vậy: nếu
        # KHÔNG có claim thật (không ai gắn category/provider/model thật vào
        # run_context) mà gate lại có client — tức đang ở nhánh compliance-
        # gated — PHẢI deny ngay, KHÔNG được suy đoán category/provider/model
        # mặc định rồi rơi về `redactor.sanitize()` (đây chính là hành vi
        # "tests green, feature inert" mà audit phát hiện ở Task 7).
        #
        # `self._client is None` (gate dựng tay không truyền client, dùng
        # trong vài unit/smoke test đọc riêng gate) là con đường KHÔNG
        # compliance-gated — hợp lệ để giữ hành vi redactor-only cũ trong
        # giai đoạn chuyển tiếp cho tới khi có "Data Egress Context" thật
        # (xem docs/superpowers/specs/2026-08-30-data-egress-context-prerequisite.md).
        #
        # LƯU Ý QUAN TRỌNG (ghi trong task-7-report.md): vì con đường
        # compliance-gated là con đường DUY NHẤT của toàn bộ runtime sản
        # xuất, và hiện KHÔNG có capability/retrieval nào build
        # `DataAccessClaim` thật, nhánh deny này sẽ chặn TẤT CẢ các run thật
        # cho tới khi Data Egress Context tồn tại — đây là hệ quả cố ý, không
        # phải lỗi, theo đúng quyết định "fail-closed cho riêng đường
        # compliance-gated, không fallback che giấu" của người dùng.
        if claim is None:
            if self._client is not None:
                raise ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")
            return self._redactor.sanitize(raw_input)

        categories = list(claim.categories)
        subject_ref = claim.subject_reference

        # Personal data guard: if personal/sensitive categories requested, subject_reference must be present
        is_personal = any(cat in ("PERSONAL", "SENSITIVE_PERSONAL") for cat in categories)
        if is_personal and not subject_ref:
            raise ComplianceDenied("PROCESSING_AUTHORIZATION_MISSING")

        if self._client and hasattr(self._client, "resolve_data_use"):
            delegation_token = run_context.get("_company_delegation_token") or run_context.get(
                "delegation_token"
            )

            decision = await self._client.resolve_data_use(
                workspace_id=claim.workspace_id,
                deployment_id=claim.deployment_id,
                capability_id=claim.capability_id,
                purpose_id=claim.purpose_id,
                data_categories=categories,
                provider_key=claim.provider_key,
                model_key=claim.model_key,
                subject_reference=subject_ref,
                delegation_token=delegation_token,
            )
            if hasattr(decision, "allowed") and not decision.allowed:
                raise ComplianceDenied(getattr(decision, "denial_code", "DATA_USE_DENIED"))

            return self._redactor.minimize(raw_input, decision)

        return self._redactor.sanitize(raw_input)

    async def prepare_tool_output(
        self, run_context: Mapping[str, Any], capability_id: str, output: Any
    ) -> Any:
        if isinstance(output, str):
            return self._redactor.sanitize(output)
        if isinstance(output, dict):
            import json

            sanitized_str = self._redactor.sanitize(json.dumps(output))
            return json.loads(sanitized_str)
        return output

    async def assert_before_model_call(self, run_context: Mapping[str, Any]) -> None:
        if "compliance_snapshot" in run_context:
            snap = run_context["compliance_snapshot"]
            status = snap.get("status") if isinstance(snap, dict) else getattr(snap, "status", None)
            if status and status != "APPROVED_FOR_USE":
                raise ComplianceDenied("DEPLOYMENT_NOT_APPROVED")
