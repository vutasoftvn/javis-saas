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

    return [
        ToolSpec(name="workspace_get", description="Lấy thông tin Workspace theo ID", handler=workspace_get),
        # workspace_list, organization_get, workforce_member_list đã bị GỠ
        # (không redirect) — xác nhận qua real HTTP (curl 404) 2026-08-22:
        # không có route nào trong services/identity backing 3 tool này
        # (không có listWorkspaces, không có getOrganization theo id, không
        # có list-workforce-members-theo-workspace). Cùng loại bug ADR-012
        # đã tìm thấy và sửa cho OKR/12WY (path sai) và legal_obligation_list
        # (route không tồn tại) — xem
        # docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md
        # "Follow-up: 3 broken identity/commercial list-style tools found"
        # (2026-08-22). Thêm endpoint thật để phục hồi 3 tool này là tính
        # năng mới, không phải sửa lỗi path — không tự làm ở đây.
    ]
