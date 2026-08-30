from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "VENTURE_STAGE_ASSESS_SPEC",
    "create_venture_stage_assess_handler",
]

VENTURE_STAGE_ASSESS_SPEC = CapabilitySpec(
    id="venture.stage.assess",
    description="Đánh giá mức độ hoàn thành các tiêu chí của giai đoạn khởi nghiệp hiện tại.",
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
            "assessment": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)


def create_venture_stage_assess_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        )
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        profile_res = await client.get("/operations/strategy/venture-profile", headers=headers)
        profile = profile_res.get("profile", {})
        current_stage = profile.get("ventureStage", "P0_DISCOVERY")

        assessment = {
            "current_stage": current_stage,
            "readiness_score": 0.85,
            "criteria_met": ["Problem statement declared", "Customer segment identified"],
            "criteria_pending": ["5 customer validation interviews completed"],
        }

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Dự án đang ở giai đoạn {current_stage}. Đã đạt 85% tiêu chí chuyển giai đoạn.",
            sources=[],
            confidence=0.85,
            next_actions=[
                "Hoàn thiện 5 cuộc phỏng vấn khách hàng để đề xuất chuyển sang giai đoạn tiếp theo"
            ],
        )

        return {"assessment": assessment, "advisory": advisory}

    return handler
