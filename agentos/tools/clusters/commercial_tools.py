from __future__ import annotations

from typing import Any, Optional
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolSpec


def get_commercial_tools(client: Optional[EncoreClient] = None) -> list[ToolSpec]:
    client = client or EncoreClient()

    async def lead_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo Sales Lead mới trong Commercial Cluster."""
        return await client.post("/commercial/leads", json=args)

    async def lead_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách Sales Lead theo workspaceId."""
        return await client.get("/commercial/leads", params=args)

    async def lead_update_stage(args: dict[str, Any]) -> dict[str, Any]:
        """Cập nhật giai đoạn xử lý của Sales Lead."""
        lead_id = args.get("id")
        stage = args.get("stage")
        return await client.post(f"/commercial/leads/{lead_id}/stage", json={"stage": stage})

    async def opportunity_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo cơ hội bán hàng (Sales Opportunity)."""
        return await client.post("/commercial/opportunities", json=args)

    async def opportunity_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách Sales Opportunities theo workspaceId."""
        return await client.get("/commercial/opportunities", params=args)

    async def opportunity_update_stage(args: dict[str, Any]) -> dict[str, Any]:
        """Cập nhật stage cho Sales Opportunity (prospecting, qualified, proposal, negotiation, closed_won, closed_lost)."""
        opp_id = args.get("id")
        stage = args.get("stage")
        return await client.post(f"/commercial/opportunities/{opp_id}/stage", json={"stage": stage})

    async def account_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo Account doanh nghiệp đối tác/khách hàng."""
        return await client.post("/commercial/accounts", json=args)

    async def contact_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo Contact người liên hệ."""
        return await client.post("/commercial/contacts", json=args)

    return [
        ToolSpec(name="lead_create", description="Tạo Sales Lead mới", handler=lead_create, permission_class="MODIFY_BUSINESS_DATA"),
        ToolSpec(name="lead_list", description="Lấy danh sách Sales Lead", handler=lead_list),
        ToolSpec(name="lead_update_stage", description="Cập nhật giai đoạn Sales Lead", handler=lead_update_stage, permission_class="MODIFY_BUSINESS_DATA"),
        ToolSpec(name="opportunity_create", description="Tạo cơ hội bán hàng", handler=opportunity_create, permission_class="MODIFY_BUSINESS_DATA"),
        ToolSpec(name="opportunity_list", description="Lấy danh sách cơ hội bán hàng", handler=opportunity_list),
        ToolSpec(name="opportunity_update_stage", description="Cập nhật stage cơ hội bán hàng", handler=opportunity_update_stage, permission_class="MODIFY_BUSINESS_DATA"),
        ToolSpec(name="account_create", description="Tạo Account doanh nghiệp", handler=account_create, permission_class="MODIFY_BUSINESS_DATA"),
        ToolSpec(name="contact_create", description="Tạo Contact người liên hệ", handler=contact_create, permission_class="MODIFY_BUSINESS_DATA"),
    ]
