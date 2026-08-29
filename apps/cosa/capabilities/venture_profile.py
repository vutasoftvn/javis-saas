from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "VENTURE_PROFILE_READ_SPEC",
    "VENTURE_PROFILE_PROPOSE_UPDATE_SPEC",
    "create_venture_profile_read_handler",
    "create_venture_profile_propose_update_handler",
]

VENTURE_PROFILE_READ_SPEC = CapabilitySpec(
    id="venture.profile.read",
    description="Đọc hồ sơ khởi nghiệp (industry, target customer, problem statement, runway) từ services/company.",
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
            "profile": {"type": "object"},
        },
    },
)

VENTURE_PROFILE_PROPOSE_UPDATE_SPEC = CapabilitySpec(
    id="venture.profile.propose_update",
    description="Cập nhật hoặc đề xuất cập nhật thông tin hồ sơ khởi nghiệp của workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "integer"},
            "problem_statement": {"type": "string"},
            "target_customer": {"type": "string"},
            "industry": {"type": "string"},
            "geography": {"type": "string"},
            "currency": {"type": "string"},
            "timezone": {"type": "string"},
            "founder_goal": {"type": "string"},
            "initial_runway_months": {"type": "integer"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "profile": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)


def create_venture_profile_read_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or getattr(context, "workspace_id", None)
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        res = await client.get("/operations/strategy/venture-profile", headers=headers)
        return {"profile": res.get("profile")}

    return handler


def create_venture_profile_propose_update_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or getattr(context, "workspace_id", None)
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        body = {
            "problemStatement": payload.get("problem_statement"),
            "targetCustomer": payload.get("target_customer"),
            "industry": payload.get("industry"),
            "geography": payload.get("geography"),
            "currency": payload.get("currency"),
            "timezone": payload.get("timezone"),
            "founderGoal": payload.get("founder_goal"),
            "initialRunwayMonths": payload.get("initial_runway_months"),
        }

        profile = await client.put("/operations/strategy/venture-profile", json=body, headers=headers)

        advisory = wrap_advisory(
            layer="POLICY_WATCH",
            label="proposal",
            content="Đã cập nhật thông tin hồ sơ doanh nghiệp. Các phân tích thị trường và nghĩa vụ pháp lý tiếp theo sẽ áp dụng dữ liệu này.",
            sources=[],
            confidence=1.0,
            next_actions=["Xem lại các nghĩa vụ pháp lý tương thích với ngành nghề vừa chọn"],
        )

        return {
            "profile": profile,
            "advisory": advisory,
        }

    return handler
