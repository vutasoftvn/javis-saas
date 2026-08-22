from __future__ import annotations

from typing import Any, Optional
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolSpec


def get_operations_tools(client: Optional[EncoreClient] = None) -> list[ToolSpec]:
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
        return await client.post("/operations/okrs/cycles", json=args)

    async def okr_objective_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo mục tiêu Objective trong chu kỳ OKR."""
        return await client.post("/operations/okrs/objectives", json=args)

    async def okr_key_result_update_progress(args: dict[str, Any]) -> dict[str, Any]:
        """Cập nhật tiến độ Key Result trong OKR."""
        kr_id = args.get("id")
        current_value = args.get("currentValue")
        return await client.post(f"/operations/okrs/key-results/{kr_id}/progress", json={"currentValue": current_value})

    async def twelve_wy_plan_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo kế hoạch 12 Week Year mới."""
        return await client.post("/operations/twelve-week-year/plans", json=args)

    async def twelve_wy_score_record(args: dict[str, Any]) -> dict[str, Any]:
        """Ghi nhận điểm thực thi tuần của kế hoạch 12 Week Year."""
        return await client.post("/operations/twelve-week-year/scores", json=args)

    async def initiative_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo sáng kiến chiến lược (Strategic Initiative)."""
        return await client.post("/operations/initiatives", json=args)

    return [
        ToolSpec(name="task_create", description="Tạo task mới trong Operations Cluster", handler=task_create),
        ToolSpec(name="task_list", description="Lấy danh sách task theo workspaceId", handler=task_list),
        ToolSpec(name="task_update_status", description="Cập nhật trạng thái task", handler=task_update_status),
        ToolSpec(name="okr_cycle_create", description="Tạo chu kỳ OKR mới", handler=okr_cycle_create),
        ToolSpec(name="okr_objective_create", description="Tạo Objective trong OKR", handler=okr_objective_create),
        ToolSpec(name="okr_key_result_update_progress", description="Cập nhật tiến độ Key Result", handler=okr_key_result_update_progress),
        ToolSpec(name="twelve_wy_plan_create", description="Tạo kế hoạch 12 Week Year", handler=twelve_wy_plan_create),
        ToolSpec(name="twelve_wy_score_record", description="Ghi nhận điểm thực thi tuần 12WY", handler=twelve_wy_score_record),
        ToolSpec(name="initiative_create", description="Tạo sáng kiến chiến lược", handler=initiative_create),
    ]
