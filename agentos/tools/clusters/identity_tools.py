from __future__ import annotations

from typing import Any, Optional
from agentos.core.policy import ToolPermission, ToolRiskLevel
from agentos.tools.encore_client import EncoreClient
from agentos.tools.spec import ToolSpecV2


def get_identity_tools(client: Optional[EncoreClient] = None) -> list[ToolSpecV2]:
    client = client or EncoreClient()

    async def workspace_get(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy thông tin chi tiết Workspace theo ID."""
        ws_id = args.get("id")
        return await client.get(f"/identity/workspaces/{ws_id}")

    return [
        ToolSpecV2(
            name="identity.workspace.get",
            version="1.0.0",
            description="Lấy thông tin Workspace theo ID",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "number"]},
                },
                "required": ["id"],
            },
            output_schema={"type": "object"},
            handler=workspace_get,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["identity", "workspace"],
        ),
    ]
