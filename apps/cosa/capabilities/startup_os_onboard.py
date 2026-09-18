from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC",
    "STARTUP_OS_ONBOARD_CADENCE_STATUS_SPEC",
    "STARTUP_OS_ONBOARD_CONTEXT_READ_SPEC",
    "STARTUP_OS_ONBOARD_DIMENSION_UPDATE_SPEC",
    "STARTUP_OS_ONBOARD_SESSION_START_SPEC",
    "STARTUP_OS_ONBOARD_SNAPSHOT_CREATE_SPEC",
    "create_startup_os_cadence_advisory_handler",
    "create_startup_os_cadence_status_handler",
    "create_startup_os_context_read_handler",
    "create_startup_os_dimension_update_handler",
    "create_startup_os_session_start_handler",
    "create_startup_os_snapshot_create_handler",
]

STARTUP_OS_ONBOARD_CONTEXT_READ_SPEC = CapabilitySpec(
    id="startup_os.onboard.context_read",
    description="Đọc ngữ cảnh chiến lược hiện tại (7 chiều dữ liệu doanh nghiệp) từ services/company.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["workspace_id"],
        "properties": {
            "workspace_id": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "workspaceId": {"type": "string"},
            "fullContext": {"type": "object"},
        },
    },
)

STARTUP_OS_ONBOARD_DIMENSION_UPDATE_SPEC = CapabilitySpec(
    id="startup_os.onboard.dimension_update",
    description="Cập nhật 1 trong 7 chiều Onboarding (append-only) cho workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["workspace_id", "session_id", "dimension", "data"],
        "properties": {
            "workspace_id": {"type": "string"},
            "session_id": {"type": "string"},
            "dimension": {
                "type": "string",
                "enum": [
                    "identity",
                    "stage_scale",
                    "founder",
                    "team_culture",
                    "market",
                    "challenges",
                    "goals_ambition",
                ],
            },
            "data": {"type": "object"},
        },
    },
    output_schema={"type": "object"},
)

STARTUP_OS_ONBOARD_SESSION_START_SPEC = CapabilitySpec(
    id="startup_os.onboard.session_start",
    description="Khởi tạo một phiên onboarding mới (/cs:setup, /cs:update, hoặc event-driven).",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["workspace_id", "session_type"],
        "properties": {
            "workspace_id": {"type": "string"},
            "session_type": {
                "type": "string",
                "enum": ["initial", "partial_update", "event_driven"],
            },
            "summary": {"type": "string"},
        },
    },
    output_schema={"type": "object"},
)

STARTUP_OS_ONBOARD_SNAPSHOT_CREATE_SPEC = CapabilitySpec(
    id="startup_os.onboard.snapshot_create",
    description="Tạo snapshot ngữ cảnh chiến lược mới đóng băng 7 chiều tại thời điểm hiện tại.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["workspace_id", "session_id"],
        "properties": {
            "workspace_id": {"type": "string"},
            "session_id": {"type": "string"},
            "change_reason": {"type": "string"},
            "changed_dimensions": {"type": "array", "items": {"type": "string"}},
        },
    },
    output_schema={"type": "object"},
)

STARTUP_OS_ONBOARD_CADENCE_STATUS_SPEC = CapabilitySpec(
    id="startup_os.onboard.cadence_status",
    description="Kiểm tra độ tươi (freshness) và các chiều cần review theo nhịp BSC.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["workspace_id"],
        "properties": {
            "workspace_id": {"type": "string"},
        },
    },
    output_schema={"type": "object"},
)


def create_startup_os_context_read_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = str(payload["workspace_id"])
        resp = await svc_client.get(
            "/operations/onboard/context/current", params={"workspaceId": ws_id}
        )
        return resp

    return handler


def create_startup_os_dimension_update_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        dimension = payload["dimension"]
        body = {
            "workspaceId": str(payload["workspace_id"]),
            "sessionId": str(payload["session_id"]),
            "data": payload["data"],
        }
        resp = await svc_client.post(f"/operations/onboard/dimensions/{dimension}", json=body)
        return resp

    return handler


def create_startup_os_session_start_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        body = {
            "workspaceId": str(payload["workspace_id"]),
            "sessionType": payload["session_type"],
            "summary": payload.get("summary"),
        }
        resp = await svc_client.post("/operations/onboard/sessions", json=body)
        return resp

    return handler


def create_startup_os_snapshot_create_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        body = {
            "workspaceId": str(payload["workspace_id"]),
            "sessionId": str(payload["session_id"]),
            "changeReason": payload.get("change_reason"),
            "changedDimensions": payload.get("changed_dimensions", []),
        }
        resp = await svc_client.post("/operations/onboard/snapshots", json=body)
        return resp

    return handler


def create_startup_os_cadence_status_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = str(payload["workspace_id"])
        resp = await svc_client.get(
            "/operations/onboard/cadence/status", params={"workspaceId": ws_id}
        )
        return resp

    return handler


STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC = CapabilitySpec(
    id="startup_os.onboard.cadence_advisory",
    description="Tính toán Freshness Score theo tuần 12WY và đề xuất rà soát ngữ cảnh (Founder toàn quyền quyết định).",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["workspace_id"],
        "properties": {
            "workspace_id": {"type": "string"},
            "snooze_weeks": {"type": "integer", "minimum": 0},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string"},
            "freshness_score": {"type": "number"},
            "status": {"type": "string"},
            "recommendations": {"type": "array"},
            "founder_authority": {"type": "string"},
        },
    },
)


def create_startup_os_cadence_advisory_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = str(payload["workspace_id"])
        resp = await svc_client.get(
            "/operations/onboard/cadence/status", params={"workspaceId": ws_id}
        )
        cadences = resp.get("cadences", []) if isinstance(resp, dict) else []

        recommendations = []
        weights = {
            "stage_scale": 0.20,
            "challenges": 0.20,
            "team_culture": 0.15,
            "market": 0.15,
            "goals_ambition": 0.15,
            "identity": 0.075,
            "founder": 0.075,
        }

        total_weight = 0.0
        weighted_score_sum = 0.0

        for item in cadences:
            dim = item.get("dimension", "")
            days = item.get("daysSinceLastReview", 0)
            interval_days = item.get("intervalDays") or 14
            weeks_since = days // 7
            interval_weeks = max(1, interval_days // 7)

            ratio = days / interval_days if interval_days > 0 else 1.0
            dim_score = max(0.0, min(100.0, 100.0 - max(0.0, (ratio - 1.0) * 50.0)))
            w = weights.get(dim, 0.1)
            weighted_score_sum += dim_score * w
            total_weight += w

            if item.get("urgency") in ("critical", "recommended"):
                recommendations.append(
                    {
                        "dimension": dim,
                        "cadence_type": item.get("cadence"),
                        "weeks_since_last_review": weeks_since,
                        "recommended_interval_weeks": interval_weeks,
                        "urgency": item.get("urgency"),
                        "advisory_nudge": (
                            f"Chiều '{dim}' đã qua {weeks_since} tuần chưa rà soát "
                            f"(nhịp đề xuất: {interval_weeks} tuần)."
                        ),
                        "available_actions": ["update_now_2min", "snooze_1w", "ignore"],
                    }
                )

        final_freshness_score = (
            round(weighted_score_sum / total_weight, 1) if total_weight > 0 else 100.0
        )
        status = (
            "fresh"
            if final_freshness_score >= 80
            else ("needs_attention" if final_freshness_score >= 50 else "stale")
        )

        return {
            "workspace_id": ws_id,
            "freshness_score": final_freshness_score,
            "status": status,
            "recommendations": recommendations,
            "founder_authority": (
                "Khuyến nghị chỉ mang tính tham khảo. Founder toàn quyền quyết định "
                "cập nhật, hoãn (snooze) hoặc bỏ qua."
            ),
        }

    return handler

