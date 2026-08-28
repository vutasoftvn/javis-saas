from __future__ import annotations

from typing import Any

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "OPERATIONS_TASK_LIST_SPEC",
    "OPERATIONS_TASK_READ_SPEC",
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
