from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "LEGAL_APPLICABILITY_ASSESS_SPEC",
    "create_legal_applicability_assess_handler",
]

LEGAL_APPLICABILITY_ASSESS_SPEC = CapabilitySpec(
    id="legal.applicability.assess",
    description="Đánh giá các nghĩa vụ pháp lý hiện hành áp dụng cho doanh nghiệp dựa trên hồ sơ pháp lý và quy định TT58/NQ86.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "integer"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "applicable_obligations": {"type": "array"},
            "advisory": {"type": "object"},
        },
    },
)


def create_legal_applicability_assess_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or getattr(context, "workspace_id", None)
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        res = await client.get("/legal/applicable-obligations", headers=headers)
        obligations = res.get("applicableObligations", [])

        sources = []
        for o in obligations:
            sources.append({
                "regulation_number": o.get("sourceRegulationNumber"),
                "version": o.get("sourceRegulationVersion"),
                "layer": o.get("layer"),
                "template_id": o.get("obligationTemplateId"),
            })

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Đã rà soát {len(obligations)} nghĩa vụ pháp lý áp dụng cho hồ sơ doanh nghiệp.",
            sources=sources,
            confidence=0.95,
            next_actions=[
                "Khởi tạo nghĩa vụ từ các mẫu áp dụng",
                "Kiểm tra hạn nộp BCTC theo TT58 nếu đã đăng ký",
            ],
        )

        return {
            "applicable_obligations": obligations,
            "advisory": advisory,
        }

    return handler
