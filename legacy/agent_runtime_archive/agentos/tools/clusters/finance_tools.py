from __future__ import annotations

from typing import Any, Optional
from agentos.core.policy import ToolPermission, ToolRiskLevel
from agentos.tools.encore_client import EncoreClient
from agentos.tools.spec import ToolSpecV2


def get_finance_tools(client: Optional[EncoreClient] = None) -> list[ToolSpecV2]:
    client = client or EncoreClient()

    async def transaction_record(args: dict[str, Any]) -> dict[str, Any]:
        """Ghi nhận giao dịch thu chi tài chính."""
        return await client.post("/finance-legal/transactions", json=args)

    async def transaction_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách giao dịch tài chính theo workspaceId."""
        return await client.get("/finance-legal/transactions", params=args)

    async def accounting_period_create(args: dict[str, Any]) -> dict[str, Any]:
        """Mở kỳ kế toán mới (Accounting Period)."""
        return await client.post("/finance-legal/accounting-periods", json=args)

    async def legal_obligation_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo nghĩa vụ pháp lý / tuân thủ cần theo dõi."""
        return await client.post("/finance-legal/obligations", json=args)

    async def legal_checklist_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo đầu mục checklist pháp lý."""
        return await client.post("/finance-legal/checklist-items", json=args)

    return [
        ToolSpecV2(
            name="finance.transaction.record",
            version="1.0.0",
            description="Ghi nhận giao dịch tài chính",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "amount": {"type": ["number", "string"]},
                    "currency": {"type": "string"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "direction": {"type": "string"},
                    "transactionDate": {"type": "string"},
                },
                "required": ["workspaceId", "amount"],
            },
            output_schema={"type": "object"},
            handler=transaction_record,
            permission_class="FINANCIAL_ACTION",
            risk_level=ToolRiskLevel.CRITICAL,
            tool_permission=ToolPermission.ADMIN_WRITE,
            write_scope="company",
            idempotent=False,
            reversible=False,
            approval_policy="always",
            audit_policy="full",
            timeout_seconds=15,
            tags=["finance", "transaction"],
        ),
        ToolSpecV2(
            name="finance.transaction.list",
            version="1.0.0",
            description="Lấy danh sách giao dịch tài chính",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                },
                "required": ["workspaceId"],
            },
            output_schema={"type": "object"},
            handler=transaction_list,
            risk_level=ToolRiskLevel.LOW,
            tool_permission=ToolPermission.READ_ONLY,
            write_scope="none",
            idempotent=True,
            reversible=True,
            approval_policy="never",
            audit_policy="minimal",
            timeout_seconds=15,
            tags=["finance", "transaction"],
        ),
        ToolSpecV2(
            name="finance.accounting_period.create",
            version="1.0.0",
            description="Tạo kỳ kế toán mới",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "periodName": {"type": "string"},
                    "startDate": {"type": "string"},
                    "endDate": {"type": "string"},
                },
                "required": ["workspaceId"],
            },
            output_schema={"type": "object"},
            handler=accounting_period_create,
            permission_class="FINANCIAL_ACTION",
            risk_level=ToolRiskLevel.CRITICAL,
            tool_permission=ToolPermission.ADMIN_WRITE,
            write_scope="company",
            idempotent=False,
            reversible=False,
            approval_policy="always",
            audit_policy="full",
            timeout_seconds=15,
            tags=["finance", "accounting"],
        ),
        ToolSpecV2(
            name="finance.legal_obligation.create",
            version="1.0.0",
            description="Tạo nghĩa vụ pháp lý",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                    "dueDate": {"type": "string"},
                },
                "required": ["workspaceId", "title"],
            },
            output_schema={"type": "object"},
            handler=legal_obligation_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="company",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["finance", "legal"],
        ),
        ToolSpecV2(
            name="finance.legal_checklist.create",
            version="1.0.0",
            description="Tạo đầu mục checklist pháp lý",
            input_schema={
                "type": "object",
                "properties": {
                    "workspaceId": {"type": ["string", "number"]},
                    "title": {"type": "string"},
                },
                "required": ["workspaceId", "title"],
            },
            output_schema={"type": "object"},
            handler=legal_checklist_create,
            permission_class="MODIFY_BUSINESS_DATA",
            risk_level=ToolRiskLevel.MEDIUM,
            tool_permission=ToolPermission.SCOPED_WRITE,
            write_scope="company",
            idempotent=False,
            reversible=True,
            approval_policy="conditional",
            audit_policy="full",
            timeout_seconds=15,
            tags=["finance", "legal"],
        ),
    ]
