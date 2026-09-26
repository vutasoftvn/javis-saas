"""Capability Goal của Startup OS (plan 2026-09-18, Phase 3 — Task 3.2).

Agent được ĐỌC cây Goal, danh sách Goal cần review và nhận tư vấn đặt Goal
(`startup_os.goal.advisory`). Tạo Goal và triage discovery Project là quyết định của
Founder ("Onboard inform, not control"): `startup_os.goal.create` và
`startup_os.project.triage` được định nghĩa cho UI/workflow nội bộ nhưng KHÔNG đăng
ký vào registry của agent và Company không mở delegation cho hai endpoint đó.

Scope luôn lấy từ InvocationContext của run, không từ tham số model sinh ra.
"""

from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.startup_os_onboard import (
    context_workspace_id,
    summarize_cadence_freshness,
)

__all__ = [
    "STARTUP_OS_GOALS_NEEDING_REVIEW_SPEC",
    "STARTUP_OS_GOAL_ADVISORY_SPEC",
    "STARTUP_OS_GOAL_CREATE_SPEC",
    "STARTUP_OS_GOAL_TREE_READ_SPEC",
    "STARTUP_OS_PROJECT_TRIAGE_SPEC",
    "build_goal_advisory",
    "create_startup_os_goal_advisory_handler",
    "create_startup_os_goal_create_handler",
    "create_startup_os_goal_tree_read_handler",
    "create_startup_os_goals_needing_review_handler",
    "create_startup_os_project_triage_handler",
]

STARTUP_OS_GOAL_CREATE_SPEC = CapabilitySpec(
    id="startup_os.goal.create",
    description="Tạo mục tiêu mới trong cây Goal phân tầng (Vision/Strategic/Tactical/Sprint) kèm kiểm tra ngữ cảnh và liên kết snapshot.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["title", "goal_type"],
        "properties": {
            "parent_id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "goal_type": {
                "type": "string",
                "enum": ["vision", "strategic", "tactical", "sprint"],
            },
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
            "duration_weeks": {"type": "number"},
            "status": {"type": "string", "enum": ["draft", "active"]},
            "snapshot_id": {"type": "string"},
        },
    },
    output_schema={"type": "object"},
)

STARTUP_OS_GOAL_TREE_READ_SPEC = CapabilitySpec(
    id="startup_os.goal.tree_read",
    description="Truy vấn toàn bộ cây Goal phân cấp lồng nhau kèm chỉ số đo lường (objectives, KRs).",
    risk=CapabilityRisk.LOW,
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
)

STARTUP_OS_GOALS_NEEDING_REVIEW_SPEC = CapabilitySpec(
    id="startup_os.goal.needing_review",
    description="Tìm các mục tiêu đang dựa trên giả định/snapshot chiến lược cũ cần được review.",
    risk=CapabilityRisk.LOW,
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
)

STARTUP_OS_PROJECT_TRIAGE_SPEC = CapabilitySpec(
    id="startup_os.project.triage",
    description="Triage các dự án khám phá (discovery projects) cuối chu kỳ (link, mark_rd, archive, roll_to_new_goal).",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id", "action"],
        "properties": {
            "project_id": {"type": "string"},
            "action": {
                "type": "string",
                "enum": ["link", "mark_rd", "archive", "roll_to_new_goal"],
            },
            "target_objective_id": {"type": "string"},
            "new_goal_id": {"type": "string"},
            "new_objective_title": {"type": "string"},
        },
    },
    output_schema={"type": "object"},
)

STARTUP_OS_GOAL_ADVISORY_SPEC = CapabilitySpec(
    id="startup_os.goal.advisory",
    description=(
        "Tư vấn trước khi Founder đặt mục tiêu: kiểm độ tươi 2 chiều Fast, gợi ý loại Goal theo "
        "giai đoạn (pre_pmf → tactical, scaling/optimizing → strategic), trả giá trị fire-worthy, "
        "ưu tiên thách thức và Goal đang cần review để đối chiếu. Chỉ tư vấn, không tạo Goal."
    ),
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "proposed_goal_type": {
                "type": "string",
                "enum": ["vision", "strategic", "tactical", "sprint"],
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "context_ready": {"type": "boolean"},
            "suggested_goal_type": {"type": ["string", "null"]},
            "warnings": {"type": "array"},
            "alignment_inputs": {"type": "object"},
            "founder_authority": {"type": "string"},
        },
    },
)


def create_startup_os_goal_create_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        body = {
            "workspaceId": context_workspace_id(context, STARTUP_OS_GOAL_CREATE_SPEC.id),
            "parentId": payload.get("parent_id"),
            "title": payload["title"],
            "description": payload.get("description"),
            "goalType": payload["goal_type"],
            "startDate": payload.get("start_date"),
            "endDate": payload.get("end_date"),
            "durationWeeks": payload.get("duration_weeks"),
            "status": payload.get("status", "active"),
            "snapshotId": payload.get("snapshot_id"),
        }
        return await svc_client.post("/operations/goals", json=body)

    return handler


def create_startup_os_goal_tree_read_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_GOAL_TREE_READ_SPEC.id)
        return await svc_client.get("/operations/goals/tree", params={"workspaceId": ws_id})

    return handler


def create_startup_os_goals_needing_review_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_GOALS_NEEDING_REVIEW_SPEC.id)
        return await svc_client.get(
            "/operations/goals/needing-review", params={"workspaceId": ws_id}
        )

    return handler


def create_startup_os_project_triage_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        body = {
            "workspaceId": context_workspace_id(context, STARTUP_OS_PROJECT_TRIAGE_SPEC.id),
            "projectId": str(payload["project_id"]),
            "action": payload["action"],
            "targetObjectiveId": payload.get("target_objective_id"),
            "newGoalId": payload.get("new_goal_id"),
            "newObjectiveTitle": payload.get("new_objective_title"),
        }
        return await svc_client.post("/operations/projects/triage", json=body)

    return handler


# Giai đoạn (onboard_stage_scale.stage) → loại Goal nên đặt cho chu kỳ tới.
_GOAL_TYPE_BY_STAGE: dict[str, str] = {
    "pre_pmf": "tactical",
    "scaling": "strategic",
    "optimizing": "strategic",
}

_FAST_DIMENSIONS = ("stage_scale", "challenges")

_PRIORITY_FIELDS: dict[str, str] = {
    "priorityProduct": "product",
    "priorityGrowth": "growth",
    "priorityPeople": "people",
    "priorityMoney": "money",
    "priorityOperations": "operations",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_goal_advisory(
    full_context: dict[str, Any],
    cadences: list[dict[str, Any]],
    goals_needing_review: list[dict[str, Any]],
    proposed_goal_type: str | None = None,
) -> dict[str, Any]:
    """Tư vấn đặt Goal từ dữ liệu có cấu trúc — không suy diễn từ văn bản tự do."""
    warnings: list[dict[str, Any]] = []

    freshness = summarize_cadence_freshness(cadences)
    stale_fast = [
        r
        for r in freshness["recommendations"]
        if r["dimension"] in _FAST_DIMENSIONS and r["urgency"] in ("critical", "recommended")
    ]
    for rec in stale_fast:
        warnings.append(
            {
                "code": "FAST_CONTEXT_STALE",
                "dimension": rec["dimension"],
                "message": rec["advisory_nudge"],
                "suggested_action": "/cs:update",
            }
        )

    stage = _as_dict(full_context.get("stage_scale")).get("stage")
    suggested = _GOAL_TYPE_BY_STAGE.get(str(stage)) if stage else None
    if suggested is None:
        warnings.append(
            {
                "code": "STAGE_UNKNOWN",
                "dimension": "stage_scale",
                "message": "Chưa ghi nhận giai đoạn startup nên chưa gợi ý được loại Goal.",
                "suggested_action": "/cs:update",
            }
        )
    elif (
        proposed_goal_type
        and proposed_goal_type in ("strategic", "tactical")
        and (proposed_goal_type != suggested)
    ):
        warnings.append(
            {
                "code": "GOAL_TYPE_MISMATCH_STAGE",
                "dimension": "stage_scale",
                "message": (
                    f"Giai đoạn '{stage}' thường hợp với Goal '{suggested}', "
                    f"Founder đang đề xuất '{proposed_goal_type}'."
                ),
                "suggested_action": None,
            }
        )

    identity = _as_dict(full_context.get("identity"))
    raw_values = identity.get("values")
    values: list[Any] = raw_values if isinstance(raw_values, list) else []
    fire_worthy = [
        str(v.get("valueText"))
        for v in values
        if isinstance(v, dict) and v.get("isFireWorthy") and v.get("valueText")
    ]

    challenges = _as_dict(full_context.get("challenges"))
    priorities = {
        area: challenges[field]
        for field, area in _PRIORITY_FIELDS.items()
        if isinstance(challenges.get(field), int)
    }
    top_score = max(priorities.values(), default=None)
    top_areas = sorted(a for a, v in priorities.items() if v == top_score) if top_score else []

    ambition = _as_dict(full_context.get("goals_ambition"))

    if goals_needing_review:
        warnings.append(
            {
                "code": "GOALS_NEED_REVIEW",
                "dimension": None,
                "message": f"{len(goals_needing_review)} Goal đang dựa trên snapshot ngữ cảnh cũ.",
                "suggested_action": None,
            }
        )

    return {
        "context_ready": not stale_fast and suggested is not None,
        "suggested_goal_type": suggested,
        "stage": stage,
        "freshness_score": freshness["freshness_score"],
        "warnings": warnings,
        "alignment_inputs": {
            "fire_worthy_values": fire_worthy,
            "top_priority_areas": top_areas,
            "priority_scores": priorities,
            "avoided_decision": challenges.get("avoidedDecision"),
            "goal_12_months": ambition.get("goal12MonthsText"),
        },
        "goals_needing_review": goals_needing_review,
        "founder_authority": (
            "Chỉ là tư vấn. Founder quyết định có tạo Goal hay không và tạo trên màn Cây mục tiêu."
        ),
    }


def create_startup_os_goal_advisory_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = context_workspace_id(context, STARTUP_OS_GOAL_ADVISORY_SPEC.id)
        params = {"workspaceId": ws_id}
        ctx_resp = await svc_client.get("/operations/onboard/context/current", params=params)
        cadence_resp = await svc_client.get("/operations/onboard/cadence/status", params=params)
        review_resp = await svc_client.get("/operations/goals/needing-review", params=params)

        full_context = _as_dict(_as_dict(ctx_resp).get("fullContext"))
        cadences = _as_dict(cadence_resp).get("cadences") or []
        needing_review = _as_dict(review_resp).get("goals") or []
        proposed = payload.get("proposed_goal_type")
        return {
            "workspace_id": ws_id,
            **build_goal_advisory(
                full_context,
                cadences if isinstance(cadences, list) else [],
                needing_review if isinstance(needing_review, list) else [],
                proposed if isinstance(proposed, str) else None,
            ),
        }

    return handler
