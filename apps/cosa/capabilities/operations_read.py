from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "OPERATIONS_EXECUTION_PLAN_READ_SPEC",
    "OPERATIONS_TASK_LIST_SPEC",
    "OPERATIONS_TASK_READ_SPEC",
    "create_operations_execution_plan_read_handler",
    "create_operations_task_list_handler",
    "create_operations_task_read_handler",
]

OPERATIONS_TASK_LIST_SPEC = CapabilitySpec(
    id="operations.task.list",
    description="Truy xuất danh sách công việc thuộc phân hệ Operations từ services/company.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "integer"},
            "status": {"type": "string"},
            "limit": {"type": "integer"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "tasks": {"type": "array"},
            "total": {"type": "integer"},
        },
    },
)

OPERATIONS_TASK_READ_SPEC = CapabilitySpec(
    id="operations.task.read",
    description="Đọc chi tiết một công việc cụ thể theo task_id từ services/company.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["task_id"],
        "properties": {
            "task_id": {"type": "integer"},
            "workspace_id": {"type": "integer"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "task": {"type": "object"},
        },
    },
)


def create_operations_task_list_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handle_task_list(payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        workspace_id = payload.get("workspace_id") or ctx.get("workspace_id", 1)
        params = {"workspaceId": workspace_id}
        if "status" in payload:
            params["status"] = payload["status"]
        if "limit" in payload:
            params["limit"] = payload["limit"]

        res = await svc_client.get("/operations/tasks", params=params)
        return res

    return handle_task_list


def create_operations_task_read_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handle_task_read(payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        task_id = payload["task_id"]
        res = await svc_client.get(f"/operations/tasks/{task_id}")
        return res

    return handle_task_read


OPERATIONS_EXECUTION_PLAN_READ_SPEC = CapabilitySpec(
    id="operations.execution_plan.read",
    description=(
        "Đọc kế hoạch triển khai (execution plan) của Project hiện tại và tiến độ: "
        "từng việc, agent phụ trách, lớp quyền hạn, trạng thái task; kèm trạng thái "
        "phân rã mục tiêu tuần gần nhất. Dùng khi founder hỏi kế hoạch/tiến độ."
    ),
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {"type": "string", "minLength": 1},
            "status": {
                "type": "string",
                "enum": ["draft", "accepted", "superseded", "rejected"],
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "plans": {"type": "array"},
            "latest_decomposition": {"type": ["object", "null"]},
        },
    },
)

_PLAN_ITEM_FIELDS = (
    "title",
    "ownerAgentProfile",
    "autonomyClass",
    "expectedCapability",
    "status",
    "taskStatus",
    "priority",
)


def _summarize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Rút gọn plan cho model: bỏ evidence/decisionReason dài, thêm đếm tiến độ."""
    items = [i for i in (plan.get("items") or []) if i.get("status") != "dropped"]
    counts: dict[str, int] = {}
    for it in items:
        key = it.get("taskStatus") or "not_materialized"
        counts[key] = counts.get(key, 0) + 1
    return {
        "id": plan.get("id"),
        "goal_text": plan.get("goalText"),
        "status": plan.get("status"),
        "origin": plan.get("origin"),
        "progress": {"total": len(items), "by_task_status": counts},
        "items": [{k: it.get(k) for k in _PLAN_ITEM_FIELDS} for it in items],
    }


def create_operations_execution_plan_read_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        )
        if not ws_id:
            # Scope lấy từ run đã verify, không từ input model sinh (fail closed).
            raise ValueError("operations.execution_plan.read: workspace_id missing from context")
        project_id = str(payload.get("project_id") or "").strip()
        if not project_id:
            raise ValueError("operations.execution_plan.read: project_id is required")
        params: dict[str, Any] = {"projectId": project_id}
        if payload.get("status"):
            params["status"] = payload["status"]
        res = await svc_client.get(
            "/operations/execution-plans",
            params=params,
            headers={"X-Workspace-Id": str(ws_id)},
        )
        return {
            "plans": [_summarize_plan(p) for p in (res.get("plans") or [])],
            "latest_decomposition": res.get("latestDecomposition"),
        }

    return handler
