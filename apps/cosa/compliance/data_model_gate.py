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

        # Task 7 audit (2026-08-30) khoá bất kỳ run compliance-gated nào thiếu
        # DataAccessClaim thật — nhưng ban đầu áp dụng cho MỌI run có client
        # thật, kể cả autopilot/copilot, vốn không hề nhận input trực tiếp
        # từ người dùng (RunRequest.input của chúng chỉ là task descriptor:
        # thread_id/contact_id/intent, không phải free text ai đó đã phân
        # loại). Sửa lại (xem
        # docs/superpowers/specs/2026-08-30-autopilot-copilot-initial-input-unblock-design.md):
        # deny chỉ áp dụng cho spec THẬT SỰ khai báo `model_input_capability_ref`
        # (tức tuyên bố nó nhận direct model input cần phân loại — hiện chỉ
        # có specs chat). Spec không khai báo capability này (autopilot/
        # copilot) rơi về `redactor.sanitize()` — đúng hành vi trước khi có
        # toàn bộ đợt hardening này, không hơn không kém. Đây KHÔNG kiểm soát
        # dữ liệu khách hàng thật mà autopilot/copilot lấy qua tool call sau
        # đó — xem "Non-Goals" trong spec doc, đó là gap riêng chưa xử lý.
        if claim is None:
            if self._client is not None and run_context.get("model_input_capability_ref"):
                raise ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")
            return self._redactor.sanitize(raw_input)

        categories = list(claim.categories)
        subject_ref = claim.subject_reference

        # Personal data guard: if personal/sensitive categories requested, subject_reference must be present
        is_personal = any(cat in ("PERSONAL", "SENSITIVE_PERSONAL") for cat in categories)
        if is_personal and not subject_ref:
            raise ComplianceDenied("PROCESSING_AUTHORIZATION_MISSING")

        if self._client is not None:
            # P1.2 — trước đây `hasattr(self._client, "resolve_data_use")` gác
            # cả nhánh này: 1 client thật thiếu đúng method đó (typo, refactor,
            # hoặc client type khác) sẽ ÂM THẦM rơi về `redactor.sanitize()`
            # không kiểm tra category/provider/authorization nào — đúng lớp
            # lỗi đã gây dead-code enforcement thật trước Task 7 (xem comment
            # `apps/cosa/capabilities/client.py::resolve_data_use`). `self._client
            # is not None` đã đủ điều kiện gọi enforcement thật; nếu client
            # thiếu method, để AttributeError raise thẳng (fail-loud) thay vì
            # hasattr nuốt lỗi thành fail-open.
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
            # Hợp đồng resolve_data_use() luôn trả object có `.allowed` (xem
            # CompanyServiceClient.resolve_data_use — SimpleNamespace với
            # default False) — không hasattr-guard thuộc tính bắt buộc theo
            # hợp đồng, để vi phạm hợp đồng lộ ra thành lỗi thay vì fail-open.
            if not decision.allowed:
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
