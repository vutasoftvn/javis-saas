from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "FINANCE_CONNECTION_READ_SPEC",
    "FINANCE_TRANSACTION_READ_SPEC",
    "create_finance_connection_read_handler",
    "create_finance_transaction_read_handler",
]

FINANCE_CONNECTION_READ_SPEC = CapabilitySpec(
    id="finance.connection.read",
    description="Đọc danh sách kết nối ngân hàng / cổng thanh toán của workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "integer"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "connections": {"type": "array"},
        },
    },
)

FINANCE_TRANSACTION_READ_SPEC = CapabilitySpec(
    id="finance.transaction.read",
    description="Đọc các giao dịch ngân hàng đã đồng bộ về workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "integer"},
            "status": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "transactions": {"type": "array"},
        },
    },
)


def create_finance_connection_read_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or getattr(context, "workspace_id", None)
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        res = await client.get("/finance/bank-connections", headers=headers)
        return {"connections": res.get("connections", [])}

    return handler


def create_finance_transaction_read_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or getattr(context, "workspace_id", None)
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        params = {}
        if payload.get("status"):
            params["status"] = payload["status"]

        res = await client.get("/finance/bank-transactions", params=params, headers=headers)
        return {"transactions": res.get("transactions", [])}

    return handler
