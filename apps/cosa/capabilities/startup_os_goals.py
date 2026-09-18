from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "STARTUP_OS_GOALS_NEEDING_REVIEW_SPEC",
    "STARTUP_OS_GOAL_CREATE_SPEC",
    "STARTUP_OS_GOAL_TREE_READ_SPEC",
    "STARTUP_OS_PROJECT_TRIAGE_SPEC",
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
        "required": ["workspace_id", "title", "goal_type"],
        "properties": {
            "workspace_id": {"type": "string"},
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
    input_schema={
        "type": "object",
        "required": ["workspace_id"],
        "properties": {
            "workspace_id": {"type": "string"},
        },
    },
    output_schema={"type": "object"},
)

STARTUP_OS_GOALS_NEEDING_REVIEW_SPEC = CapabilitySpec(
    id="startup_os.goal.needing_review",
    description="Tìm các mục tiêu đang dựa trên giả định/snapshot chiến lược cũ cần được review.",
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

STARTUP_OS_PROJECT_TRIAGE_SPEC = CapabilitySpec(
    id="startup_os.project.triage",
    description="Triage các dự án khám phá (discovery projects) cuối chu kỳ (link, mark_rd, archive, roll_to_new_goal).",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["workspace_id", "project_id", "action"],
        "properties": {
            "workspace_id": {"type": "string"},
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


def create_startup_os_goal_create_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        body = {
            "workspaceId": str(payload["workspace_id"]),
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
        resp = await svc_client.post("/operations/goals", json=body)
        return resp

    return handler


def create_startup_os_goal_tree_read_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = str(payload["workspace_id"])
        resp = await svc_client.get("/operations/goals/tree", params={"workspaceId": ws_id})
        return resp

    return handler


def create_startup_os_goals_needing_review_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = str(payload["workspace_id"])
        resp = await svc_client.get(
            "/operations/goals/needing-review", params={"workspaceId": ws_id}
        )
        return resp

    return handler


def create_startup_os_project_triage_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        body = {
            "workspaceId": str(payload["workspace_id"]),
            "projectId": str(payload["project_id"]),
            "action": payload["action"],
            "targetObjectiveId": payload.get("target_objective_id"),
            "newGoalId": payload.get("new_goal_id"),
            "newObjectiveTitle": payload.get("new_objective_title"),
        }
        resp = await svc_client.post("/operations/projects/triage", json=body)
        return resp

    return handler
