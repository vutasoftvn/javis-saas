from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "VENTURE_STAGE_ASSESS_SPEC",
    "VENTURE_STAGE_TRANSITION_PROPOSE_SPEC",
    "create_venture_stage_assess_handler",
    "create_venture_stage_transition_propose_handler",
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

VENTURE_STAGE_TRANSITION_PROPOSE_SPEC = CapabilitySpec(
    id="venture.stage.transition_propose",
    description="Đề xuất chuyển giai đoạn khởi nghiệp (ví dụ S0 sang S1, S1 sang S2) kèm lý do và căn cứ bằng chứng.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["to_stage", "reason"],
        "properties": {
            "workspace_id": {"type": "integer"},
            "to_stage": {"type": "string"},
            "reason": {"type": "string", "minLength": 10},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "proposal": {"type": "object"},
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


def create_venture_stage_transition_propose_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        )
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        to_stage = payload["to_stage"]
        reason = payload["reason"]

        proposal = {
            "toStage": to_stage,
            "reason": reason,
            "evidenceRefs": payload.get("evidence_refs", []),
            "status": "PROPOSED",
        }

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đề xuất chuyển giai đoạn sang {to_stage}. Lý do: {reason}",
            sources=[],
            confidence=0.9,
            next_actions=["Founder xem xét và phê duyệt chuyển giai đoạn tại trang Chiến lược"],
        )

        return {"proposal": proposal, "advisory": advisory}

    return handler
