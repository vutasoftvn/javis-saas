from __future__ import annotations

from typing import Any, Optional
from agentos.core.policy import ToolPermission, ToolRiskLevel
from agentos.tools.encore_client import EncoreClient
from agentos.tools.spec import ToolSpecV2


def get_operations_tools(client: Optional[EncoreClient] = None) -> list[ToolSpecV2]:
    client = client or EncoreClient()

    async def task_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo task mới trong Operations Cluster."""
        return await client.post("/operations/tasks", json=args)

    async def task_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách task theo workspaceId."""
        return await client.get("/operations/tasks", params=args)

    async def task_update_status(args: dict[str, Any]) -> dict[str, Any]:
        """Cập nhật trạng thái task (todo, in_progress, waiting_approval, blocked, done, cancelled)."""
        task_id = args.get("id")
        status = args.get("status")
        return await client.post(f"/operations/tasks/{task_id}/status", json={"status": status})

    async def okr_cycle_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo chu kỳ OKR mới (ví dụ: Q1-2026, Q2-2026)."""
        return await client.post("/operations/okr-cycles", json=args)

    async def okr_objective_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo mục tiêu Objective trong chu kỳ OKR."""
        return await client.post("/operations/objectives", json=args)

    async def okr_key_result_update_progress(args: dict[str, Any]) -> dict[str, Any]:
        """Cập nhật tiến độ Key Result trong OKR."""
        kr_id = args.get("id")
        current_value = args.get("currentValue")
        return await client.post(f"/operations/key-results/{kr_id}/checkin", json={"value": current_value})

    async def twelve_wy_plan_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo kế hoạch 12 Week Year mới (12-week cycle)."""
        return await client.post("/operations/cycles", json=args)

    async def initiative_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo sáng kiến chiến lược (Strategic Initiative)."""
        return await client.post("/operations/initiatives", json=args)

    return [
        ToolSpecV2(
            name="operations.task.create",
            version="1.0.0",
            description="Tạo task mới trong Operations Cluster",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "function": {"type": "string"},
                    "assigneeId": {"type": ["string", "number"]},
                },
                "required": ["workspaceId", "title"],
            },
            output_schema={"type": "object"},
            handler=task_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["operations", "task"],
        ),
        ToolSpecV2(
            name="operations.task.list",
            version="1.0.0",
            description="Lấy danh sách task theo workspaceId",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "status": {"type": "string"},
                    "function": {"type": "string"},
                },
                "required": ["workspaceId"],
            },
            output_schema={"type": "object"},
            handler=task_list,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["operations", "task"],
        ),
        ToolSpecV2(
            name="operations.task.update_status",
            version="1.0.0",
            description="Cập nhật trạng thái task",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "number"]},
                    "status": {"type": "string"},
                },
                "required": ["id", "status"],
            },
            output_schema={"type": "object"},
            handler=task_update_status,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=True,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["operations", "task"],
        ),
        ToolSpecV2(
            name="operations.okr_cycle.create",
            version="1.0.0",
            description="Tạo chu kỳ OKR mới",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "name": {"type": "string"},
                    "title": {"type": "string"},
                    "startDate": {"type": "string"},
                    "endDate": {"type": "string"},
                },
                "required": ["workspaceId"],
            },
            output_schema={"type": "object"},
            handler=okr_cycle_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["operations", "okr"],
        ),
        ToolSpecV2(
            name="operations.okr_objective.create",
            version="1.0.0",
            description="Tạo Objective trong OKR",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "cycleId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["workspaceId", "cycleId", "title"],
            },
            output_schema={"type": "object"},
            handler=okr_objective_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["operations", "okr"],
        ),
        ToolSpecV2(
            name="operations.okr_key_result.update_progress",
            version="1.0.0",
            description="Cập nhật tiến độ Key Result",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "number"]},
                    "currentValue": {"type": ["string", "number"]},
                },
                "required": ["id", "currentValue"],
            },
            output_schema={"type": "object"},
            handler=okr_key_result_update_progress,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=True,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["operations", "okr"],
        ),
        ToolSpecV2(
            name="operations.twelve_wy_plan.create",
            version="1.0.0",
            description="Tạo kế hoạch 12 Week Year (12-week cycle)",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "visionStatement": {"type": "string"},
                    "theme": {"type": "string"},
                    "durationWeeks": {"type": "number"},
                },
                "required": ["workspaceId"],
            },
            output_schema={"type": "object"},
            handler=twelve_wy_plan_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["operations", "12wy"],
        ),
        ToolSpecV2(
            name="operations.initiative.create",
            version="1.0.0",
            description="Tạo sáng kiến chiến lược",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["workspaceId", "title"],
            },
            output_schema={"type": "object"},
            handler=initiative_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["operations", "initiative"],
        ),
    ]
