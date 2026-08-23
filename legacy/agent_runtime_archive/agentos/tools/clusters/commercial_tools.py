from __future__ import annotations

from typing import Any, Optional
from agentos.core.policy import ToolPermission, ToolRiskLevel
from agentos.tools.encore_client import EncoreClient
from agentos.tools.spec import ToolSpecV2


def get_commercial_tools(client: Optional[EncoreClient] = None) -> list[ToolSpecV2]:
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
        ToolSpecV2(
            name="commercial.lead.create",
            version="1.0.0",
            description="Tạo Sales Lead mới",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "company": {"type": "string"},
                },
                "required": ["workspaceId", "name"],
            },
            output_schema={"type": "object"},
            handler=lead_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["commercial", "lead"],
        ),
        ToolSpecV2(
            name="commercial.lead.list",
            version="1.0.0",
            description="Lấy danh sách Sales Lead",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "stage": {"type": "string"},
                },
                "required": ["workspaceId"],
            },
            output_schema={"type": "object"},
            handler=lead_list,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["commercial", "lead"],
        ),
        ToolSpecV2(
            name="commercial.lead.update_stage",
            version="1.0.0",
            description="Cập nhật giai đoạn Sales Lead",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "number"]},
                    "stage": {"type": "string"},
                },
                "required": ["id", "stage"],
            },
            output_schema={"type": "object"},
            handler=lead_update_stage,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=True,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["commercial", "lead"],
        ),
        ToolSpecV2(
            name="commercial.opportunity.create",
            version="1.0.0",
            description="Tạo cơ hội bán hàng",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "product": {"type": "string"},
                    "accountId": {"type": ["string", "number"]},
                    "value": {"type": ["number", "string"]},
                    "stage": {"type": "string"},
                },
                "required": ["workspaceId"],
            },
            output_schema={"type": "object"},
            handler=opportunity_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["commercial", "opportunity"],
        ),
        ToolSpecV2(
            name="commercial.opportunity.update_stage",
            version="1.0.0",
            description="Cập nhật stage cơ hội bán hàng",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "number"]},
                    "stage": {"type": "string"},
                },
                "required": ["id", "stage"],
            },
            output_schema={"type": "object"},
            handler=opportunity_update_stage,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=True,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["commercial", "opportunity"],
        ),
        ToolSpecV2(
            name="commercial.account.create",
            version="1.0.0",
            description="Tạo Account doanh nghiệp",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "name": {"type": "string"},
                    "domain": {"type": "string"},
                },
                "required": ["workspaceId", "name"],
            },
            output_schema={"type": "object"},
            handler=account_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["commercial", "account"],
        ),
        ToolSpecV2(
            name="commercial.contact.create",
            version="1.0.0",
            description="Tạo Contact người liên hệ",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["workspaceId", "name"],
            },
            output_schema={"type": "object"},
            handler=contact_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="workspace",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["commercial", "contact"],
        ),
    ]
