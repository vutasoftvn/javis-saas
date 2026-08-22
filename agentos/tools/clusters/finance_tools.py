from __future__ import annotations

from typing import Any, Optional
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolSpec


def get_finance_tools(client: Optional[EncoreClient] = None) -> list[ToolSpec]:
    client = client or EncoreClient()

    async def transaction_record(args: dict[str, Any]) -> dict[str, Any]:
        """Ghi nhận giao dịch thu chi tài chính."""
        return await client.post("/finance-legal/transactions", json=args)

    async def transaction_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách giao dịch tài chính theo workspaceId."""
        return await client.get("/finance-legal/transactions", params=args)

    async def accounting_period_create(args: dict[str, Any]) -> dict[str, Any]:
        """Mở kỳ kế toán mới (Accounting Period)."""
        return await client.post("/finance-legal/accounting/periods", json=args)

    async def legal_obligation_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo nghĩa vụ pháp lý / tuân thủ cần theo dõi."""
        return await client.post("/finance-legal/legal/obligations", json=args)

    async def legal_obligation_list(args: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách nghĩa vụ pháp lý theo workspaceId."""
        return await client.get("/finance-legal/legal/obligations", params=args)

    async def legal_checklist_create(args: dict[str, Any]) -> dict[str, Any]:
        """Tạo đầu mục checklist pháp lý."""
        return await client.post("/finance-legal/legal/checklists", json=args)

    return [
        ToolSpec(name="transaction_record", description="Ghi nhận giao dịch tài chính", handler=transaction_record),
        ToolSpec(name="transaction_list", description="Lấy danh sách giao dịch tài chính", handler=transaction_list),
        ToolSpec(name="accounting_period_create", description="Tạo kỳ kế toán mới", handler=accounting_period_create),
        ToolSpec(name="legal_obligation_create", description="Tạo nghĩa vụ pháp lý", handler=legal_obligation_create),
        ToolSpec(name="legal_obligation_list", description="Lấy danh sách nghĩa vụ pháp lý", handler=legal_obligation_list),
        ToolSpec(name="legal_checklist_create", description="Tạo đầu mục checklist pháp lý", handler=legal_checklist_create),
    ]
