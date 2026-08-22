from __future__ import annotations

from typing import Any, Optional
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolSpec


def get_identity_tools(client: Optional[EncoreClient] = None) -> list[ToolSpec]:
    client = client or EncoreClient()

    async def workspace_get(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy thông tin chi tiết Workspace theo ID."""
        ws_id = args.get("id")
        return await client.get(f"/identity/workspaces/{ws_id}")

    async def workspace_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách tất cả Workspace."""
        return await client.get("/identity/workspaces")

    async def organization_get(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy thông tin Organization."""
        org_id = args.get("id")
        return await client.get(f"/identity/organizations/{org_id}")

    async def workforce_member_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách thành viên nhân sự (Workforce Members) trong Workspace."""
        return await client.get("/identity/workforce-members", params=args)

    return [
        ToolSpec(name="workspace_get", description="Lấy thông tin Workspace theo ID", handler=workspace_get),
        ToolSpec(name="workspace_list", description="Lấy danh sách Workspaces", handler=workspace_list),
        ToolSpec(name="organization_get", description="Lấy thông tin Organization", handler=organization_get),
        ToolSpec(name="workforce_member_list", description="Lấy danh sách Workforce Members", handler=workforce_member_list),
    ]
