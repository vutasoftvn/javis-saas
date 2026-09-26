"""Capability Onboarding 7 chiều của Startup OS (plan 2026-09-18, Phase 3).

Luồng hội thoại `/cs:setup` (phỏng vấn đủ 7 chiều) và `/cs:update` (micro-intake 2
chiều Fast): agent đọc kịch bản qua `startup_os.onboard.interview_plan`, mở phiên
(`session_start`), ghi từng chiều Founder đã trả lời (`dimension_update`) rồi chốt
snapshot (`snapshot_create`).

Scope luôn lấy từ InvocationContext của run (`workspace_id`), KHÔNG từ tham số do
model sinh ra — delegation token Company cũng chỉ hợp lệ cho đúng workspace đó.
"""

from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.workflows.onboarding_dimensions import (
    ONBOARD_DIMENSION_FIELDS,
    ONBOARD_DIMENSIONS,
    validate_dimension_data,
)

__all__ = [
    "STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC",
    "STARTUP_OS_ONBOARD_CADENCE_STATUS_SPEC",
    "STARTUP_OS_ONBOARD_CONTEXT_READ_SPEC",
    "STARTUP_OS_ONBOARD_DIMENSION_UPDATE_SPEC",
    "STARTUP_OS_ONBOARD_INTERVIEW_PLAN_SPEC",
    "STARTUP_OS_ONBOARD_SESSION_START_SPEC",
    "STARTUP_OS_ONBOARD_SNAPSHOT_CREATE_SPEC",
    "context_workspace_id",
    "create_startup_os_cadence_advisory_handler",
    "create_startup_os_cadence_status_handler",
    "create_startup_os_context_read_handler",
    "create_startup_os_dimension_update_handler",
    "create_startup_os_interview_plan_handler",
    "create_startup_os_session_start_handler",
    "create_startup_os_snapshot_create_handler",
]


def context_workspace_id(context: Any, capability_id: str) -> str:
    """workspace_id của run hiện tại; thiếu ⇒ fail closed (không đoán scope)."""
    if isinstance(context, dict):
        workspace_id = context.get("workspace_id")
    else:
        workspace_id = getattr(context, "workspace_id", None)
    if not workspace_id or not str(workspace_id).strip():
        raise ValueError(f"{capability_id}: workspace_id missing from invocation context")
    return str(workspace_id)


def _dimension_fields_description() -> str:
    parts = [f"{dim}: {', '.join(fields)}" for dim, fields in ONBOARD_DIMENSION_FIELDS.items()]
    return "Field hợp lệ theo chiều — " + "; ".join(parts)


STARTUP_OS_ONBOARD_CONTEXT_READ_SPEC = CapabilitySpec(
    id="startup_os.onboard.context_read",
    description="Đọc ngữ cảnh chiến lược hiện tại (7 chiều dữ liệu doanh nghiệp) từ services/company.",
    risk=CapabilityRisk.LOW,
    input_schema={"type": "object", "properties": {}},
    output_schema={
        "type": "object",
        "properties": {
            "workspaceId": {"type": "string"},
            "fullContext": {"type": "object"},
        },
    },
)

STARTUP_OS_ONBOARD_INTERVIEW_PLAN_SPEC = CapabilitySpec(
    id="startup_os.onboard.interview_plan",
    description=(
        "Lấy kịch bản phỏng vấn onboarding: session_type='initial' cho /cs:setup (đủ 7 chiều), "
        "'partial_update' cho /cs:update (2 chiều Fast). Có thể gửi founder_message để phát hiện "
        "sự kiện lớn (gọi vốn, biến động nhân sự, đối thủ, pivot) cần cập nhật ngữ cảnh."
    ),
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "session_type": {"type": "string", "enum": ["initial", "partial_update"]},
            "founder_message": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "session_type": {"type": "string"},
            "steps": {"type": "array"},
            "event_trigger": {"type": "object"},
        },
    },
)

STARTUP_OS_ONBOARD_DIMENSION_UPDATE_SPEC = CapabilitySpec(
    id="startup_os.onboard.dimension_update",
    description=(
        "Ghi 1 trong 7 chiều Onboarding (append-only) từ câu trả lời Founder vừa đưa. "
        "Chỉ gửi field Founder thực sự đã trả lời. " + _dimension_fields_description()
    ),
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["session_id", "dimension", "data"],
        "properties": {
            "session_id": {"type": "string"},
            "dimension": {"type": "string", "enum": list(ONBOARD_DIMENSIONS)},
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
        "required": ["session_type"],
        "properties": {
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
    description="Chốt phiên onboarding: tạo snapshot đóng băng 7 chiều tại thời điểm hiện tại.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["session_id"],
        "properties": {
            "session_id": {"type": "string"},
            "change_reason": {"type": "string"},
            "changed_dimensions": {
                "type": "array",
                "items": {"type": "string", "enum": list(ONBOARD_DIMENSIONS)},
            },
        },
    },
    output_schema={"type": "object"},
)

STARTUP_OS_ONBOARD_CADENCE_STATUS_SPEC = CapabilitySpec(
    id="startup_os.onboard.cadence_status",
    description="Kiểm tra độ tươi (freshness) và các chiều cần review theo nhịp BSC.",
    risk=CapabilityRisk.LOW,
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
)

STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC = CapabilitySpec(
    id="startup_os.onboard.cadence_advisory",
    description="Tính toán Freshness Score theo tuần 12WY và đề xuất rà soát ngữ cảnh (Founder toàn quyền quyết định).",
    risk=CapabilityRisk.LOW,
    input_schema={"type": "object", "properties": {}},
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


def create_startup_os_context_read_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_ONBOARD_CONTEXT_READ_SPEC.id)
        return await svc_client.get(
            "/operations/onboard/context/current", params={"workspaceId": ws_id}
        )

    return handler


def create_startup_os_interview_plan_handler():
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        # Import muộn: workflows.conversational_onboarding import capabilities.client,
        # nạp ở top-level sẽ tạo vòng import khi package capabilities khởi tạo trước.
        from apps.cosa.workflows.conversational_onboarding import (
            EventTriggerDetector,
            OnboardingSessionType,
            steps_for_session,
        )

        session_type = OnboardingSessionType(payload.get("session_type") or "initial")
        result: dict[str, Any] = {
            "session_type": session_type.value,
            "steps": [step.to_dict() for step in steps_for_session(session_type)],
            "event_trigger": None,
            "rules": [
                "Hỏi lần lượt từng chiều; chỉ ghi field Founder đã thực sự trả lời.",
                "Field Founder bỏ qua thì liệt kê tên field trong notCaptured, không bịa giá trị.",
                "Gọi snapshot_create khi Founder xác nhận kết thúc phiên.",
            ],
        }
        message = payload.get("founder_message")
        if isinstance(message, str) and message.strip():
            trigger = EventTriggerDetector.detect(message)
            if trigger.triggered:
                result["event_trigger"] = {
                    "event_type": trigger.event_type,
                    "suggested_dimension": trigger.suggested_dimension,
                    "advisory_prompt": trigger.advisory_prompt,
                }
        return result

    return handler


def create_startup_os_dimension_update_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_ONBOARD_DIMENSION_UPDATE_SPEC.id)
        dimension = str(payload["dimension"])
        data = validate_dimension_data(dimension, payload.get("data"))
        body = {
            "workspaceId": ws_id,
            "sessionId": str(payload["session_id"]),
            "data": data,
        }
        return await svc_client.post(f"/operations/onboard/dimensions/{dimension}", json=body)

    return handler


def create_startup_os_session_start_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_ONBOARD_SESSION_START_SPEC.id)
        body = {
            "workspaceId": ws_id,
            "sessionType": payload["session_type"],
            "summary": payload.get("summary"),
        }
        return await svc_client.post("/operations/onboard/sessions", json=body)

    return handler


def create_startup_os_snapshot_create_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_ONBOARD_SNAPSHOT_CREATE_SPEC.id)
        body = {
            "workspaceId": ws_id,
            "sessionId": str(payload["session_id"]),
            "changeReason": payload.get("change_reason"),
            "changedDimensions": payload.get("changed_dimensions", []),
        }
        return await svc_client.post("/operations/onboard/snapshots", json=body)

    return handler


def create_startup_os_cadence_status_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_ONBOARD_CADENCE_STATUS_SPEC.id)
        return await svc_client.get(
            "/operations/onboard/cadence/status", params={"workspaceId": ws_id}
        )

    return handler


_DIMENSION_WEIGHTS: dict[str, float] = {
    "stage_scale": 0.20,
    "challenges": 0.20,
    "team_culture": 0.15,
    "market": 0.15,
    "goals_ambition": 0.15,
    "identity": 0.075,
    "founder": 0.075,
}


def summarize_cadence_freshness(cadences: list[dict[str, Any]]) -> dict[str, Any]:
    """Freshness Score + gợi ý rà soát từ `GET /operations/onboard/cadence/status`.

    Chiều chưa từng ghi nhận (`neverReviewed`) được 0 điểm và luôn được gợi ý — không
    được coi là "tươi". Danh sách rỗng ⇒ `not_started`, không phải 100 điểm.
    """
    if not cadences:
        return {"freshness_score": 0.0, "status": "not_started", "recommendations": []}

    recommendations: list[dict[str, Any]] = []
    total_weight = 0.0
    weighted_score_sum = 0.0

    for item in cadences:
        dim = str(item.get("dimension", ""))
        interval_days = int(item.get("intervalDays") or 14)
        interval_weeks = max(1, interval_days // 7)
        never_reviewed = bool(item.get("neverReviewed")) or item.get("daysSinceLastReview") is None
        weight = _DIMENSION_WEIGHTS.get(dim, 0.1)
        total_weight += weight

        if never_reviewed:
            recommendations.append(
                {
                    "dimension": dim,
                    "cadence_type": item.get("cadence"),
                    "weeks_since_last_review": None,
                    "recommended_interval_weeks": interval_weeks,
                    "urgency": "critical",
                    "never_reviewed": True,
                    "advisory_nudge": f"Chiều '{dim}' chưa từng được ghi nhận.",
                    "available_actions": ["update_now_2min", "snooze_1w", "ignore"],
                }
            )
            continue

        days = int(item.get("daysSinceLastReview") or 0)
        weeks_since = days // 7
        ratio = days / interval_days if interval_days > 0 else 1.0
        dim_score = max(0.0, min(100.0, 100.0 - max(0.0, (ratio - 1.0) * 50.0)))
        weighted_score_sum += dim_score * weight

        if item.get("urgency") in ("critical", "recommended"):
            recommendations.append(
                {
                    "dimension": dim,
                    "cadence_type": item.get("cadence"),
                    "weeks_since_last_review": weeks_since,
                    "recommended_interval_weeks": interval_weeks,
                    "urgency": item.get("urgency"),
                    "never_reviewed": False,
                    "advisory_nudge": (
                        f"Chiều '{dim}' đã qua {weeks_since} tuần chưa rà soát "
                        f"(nhịp đề xuất: {interval_weeks} tuần)."
                    ),
                    "available_actions": ["update_now_2min", "snooze_1w", "ignore"],
                }
            )

    score = round(weighted_score_sum / total_weight, 1) if total_weight > 0 else 0.0
    status = "fresh" if score >= 80 else ("needs_attention" if score >= 50 else "stale")
    return {"freshness_score": score, "status": status, "recommendations": recommendations}


def create_startup_os_cadence_advisory_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_ONBOARD_CADENCE_ADVISORY_SPEC.id)
        resp = await svc_client.get(
            "/operations/onboard/cadence/status", params={"workspaceId": ws_id}
        )
        cadences = resp.get("cadences", []) if isinstance(resp, dict) else []
        summary = summarize_cadence_freshness(cadences)
        return {
            "workspace_id": ws_id,
            **summary,
            "founder_authority": (
                "Khuyến nghị chỉ mang tính tham khảo. Founder toàn quyền quyết định "
                "cập nhật, hoãn (snooze) hoặc bỏ qua."
            ),
        }

    return handler
